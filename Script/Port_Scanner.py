import asyncio
import socket
import ssl
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
import argparse
import logging
import aiohttp
import ipaddress
import json
import time
from dataclasses import dataclass
from enum import Enum, auto
from collections import defaultdict

default_timeout = 2.0
default_concurrency = 512
max_retries = 2
Banner_grab_size= 1024

