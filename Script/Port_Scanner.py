import argparse
import ipaddress
import logging
import socket
import ssl
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime
import json
import subprocess

default_timeout = 2.0
default_concurrency = 512
max_retries = 2
banner_grab_size = 1024

# Common ports if no range is given
top_common_ports = [
    21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443,
    445, 993, 995, 1723, 3306, 3389, 5900, 8080
]

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class Scantype(Enum):
    CONNECT = auto()
    SYN = auto()
    UDP = auto()


@dataclass
class Scanresult:
    port: int
    is_open: bool
    banner: Optional[str] = None
    service: Optional[str] = None
    protocol: str = "TCP"
    response_time: Optional[float] = None
    ssl_info: Optional[Dict[str, Any]] = None


class PortScanner:
    def __init__(self, target, ports=None, timeout=default_timeout,
                 max_concurrency=default_concurrency, output_file=None,
                 verbose=False):
        self.target = target
        self.ports = ports if ports else top_common_ports
        self.timeout = timeout
        self.max_concurrency = max_concurrency
        self.output_file = output_file
        self.verbose = verbose

        self.results = []
        self.scan_stats = {
            'total_ports': len(self.ports),
            'open_ports': 0,
            'start_time': None,
            'end_time': None,
            'duration': None
        }

        self.validate_input()

    def validate_input(self):
        try:
            try:
                ipaddress.ip_address(self.target)
            except ValueError:
                socket.gethostbyname(self.target)
        except Exception as e:
            logger.error(f"Configuration error: {e}")
            raise

    async def scan_task(self, semaphore, port):
        async with semaphore:
            result = await self.test_port(port)
            if result.is_open:
                self.results.append(result)
                logger.info(f"Port {port} is open - Service: {result.service or 'Unknown'} - Banner: {result.banner or 'None'}")
            elif self.verbose:
                logger.debug(f"Port {port} is closed/filtered")

    async def test_port(self, port):
        result = Scanresult(port=port, is_open=False)
        start_time = time.monotonic()

        for attempt in range(max_retries):
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.target, port),
                    timeout=self.timeout
                )

                result.is_open = True
                result.response_time = time.monotonic() - start_time
                result.banner = await self.grab_banner(reader, writer)
                result.ssl_info = await self.check_ssl(port)
                result.service = self.detect_service(port, result.banner)

                writer.close()
                await writer.wait_closed()
                break

            except (ConnectionRefusedError, asyncio.TimeoutError):
                continue
            except OSError as e:
                if "Too many open files" in str(e):
                    logger.warning("Resource limit hit")
                    await asyncio.sleep(1)
                continue
            except Exception as e:
                if self.verbose:
                    logger.debug(f"Unexpected error: {e}")
                continue
        return result

    async def grab_banner(self, reader, writer):
        probes = [
            b'HEAD / HTTP/1.0\r\n\r\n',
            b'GET / HTTP/1.0\r\n\r\n',
            b'\r\n\r\n',
            b'HELP\r\n'
        ]

        for probe in probes:
            try:
                writer.write(probe)
                await writer.drain()
                banner = await asyncio.wait_for(
                    reader.read(banner_grab_size),
                    timeout=self.timeout
                )
                if banner:
                    return banner.decode(errors='ignore').strip()
            except Exception:
                continue
        return None

    async def check_ssl(self, port):
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    self.target,
                    port, ssl=context,
                    server_hostname=self.target),
                timeout=self.timeout
            )

            ssl_info = {
                'version': writer.get_extra_info('ssl_object').version(),
                'cipher': writer.get_extra_info('cipher'),
                'cert': None
            }

            cert = writer.get_extra_info('peercert')
            if cert:
                ssl_info['cert'] = {
                    'subject': dict(x[0] for x in cert['subject']),
                    'issuer': dict(x[0] for x in cert['issuer']),
                    'valid_from': cert['notBefore'],
                    'valid_to': cert['notAfter']
                }
            writer.close()
            await writer.wait_closed()
            return ssl_info
        except Exception:
            return None

    def detect_service(self, port, banner):
        port_services = {
            21: 'FTP', 22: 'SSH', 23: 'Telnet',
            25: 'SMTP', 53: 'DNS', 80: 'HTTP',
            110: 'POP3', 143: 'IMAP',
            443: 'HTTPS', 3306: 'MySQL', 3389: 'RDP',
            5900: 'VNC', 8080: 'HTTP-Proxy'
        }

        service = port_services.get(port)

        if banner:
            banner_lower = banner.lower()
            if 'ssh' in banner_lower:
                return 'SSH'
            elif 'http' in banner_lower:
                return 'HTTP'
            elif 'smtp' in banner_lower:
                return 'SMTP'

        return service

    async def scan(self):
        self.scan_stats['start_time'] = datetime.now()

        logger.info(f"Scanning {self.target} ({self.scan_stats['total_ports']} ports)")

        semaphore = asyncio.Semaphore(self.max_concurrency)
        tasks = []

        for port in self.ports:
            task = asyncio.create_task(self.scan_task(semaphore, port))
            tasks.append(task)

            if len(tasks) % 100 == 0:
                await asyncio.sleep(0.001)

        await asyncio.gather(*tasks)
        self.finalize_scan()

    def finalize_scan(self):
        self.scan_stats['end_time'] = datetime.now()
        self.scan_stats['duration'] = self.scan_stats['end_time'] - self.scan_stats['start_time']
        self.scan_stats['open_ports'] = len([r for r in self.results if r.is_open])
        self.results.sort(key=lambda x: x.port)
        self.generate_report()

    def generate_report(self):
        print(f"\nScan Report for {self.target}")
        print(f"Scanned {self.scan_stats['total_ports']} ports in {self.scan_stats['duration']}")
        print(f"Open ports: {self.scan_stats['open_ports']}\n")

        print(f"{'PORT':<8} {'STATE':<8} {'SERVICE':<10}")
        print("-" * 30)
        for result in self.results:
            if result.is_open:
                print(f"{result.port}/tcp  {'open':<8} {result.service or 'Unknown'}")

        if self.output_file:
            with open(self.output_file, 'w') as f:
                json.dump({
                    'metadata': self.scan_stats,
                    'results': [r.__dict__ for r in self.results]
                }, f, indent=2)
            logger.info(f"Report saved to {self.output_file}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Simple nmap-like Port Scanner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("target", help="IP address or hostname to scan")
    parser.add_argument("-p", "--ports", help="Port range (e.g., 20-80)")
    parser.add_argument("-t", "--timeout", type=float, default=default_timeout,
                        help="Connection timeout in seconds")
    parser.add_argument("-c", "--concurrency", type=int,
                        default=default_concurrency,
                        help="Maximum concurrent connections")
    parser.add_argument("-o", "--output", help="Output JSON file")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable debug output")
    return parser.parse_args()


async def ping_target(host):
    try:
        logger.info(f"Pinging {host}...")
        output = subprocess.check_output(["ping", "-c", "1", host],
                                          stderr=subprocess.DEVNULL,
                                          universal_newlines=True)
        logger.info("Ping successful")
        return True
    except subprocess.CalledProcessError:
        logger.warning("Ping failed - host might be down or blocking ICMP")
        return False


async def main():
    args = parse_args()

    try:
        if args.ports:
            if '-' in args.ports:
                start_port, end_port = map(int, args.ports.split('-'))
                ports = list(range(start_port, end_port + 1))
            else:
                ports = [int(args.ports)]
        else:
            ports = None

        await ping_target(args.target)

        scanner = PortScanner(
            target=args.target,
            ports=ports,
            timeout=args.timeout,
            max_concurrency=args.concurrency,
            output_file=args.output,
            verbose=args.verbose
        )
        await scanner.scan()
    except KeyboardInterrupt:
        logger.info("\nScan aborted by user")
    except Exception as e:
        logger.error(f"Critical failure: {e}", exc_info=args.verbose)


if __name__ == "__main__":
    asyncio.run(main())
