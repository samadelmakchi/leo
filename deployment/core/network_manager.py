#!/usr/bin/env python3
"""
Network Manager
مدیریت عملیات شبکه‌ای
"""

import logging
import socket
import subprocess
import ipaddress
from typing import Dict, Any, List, Optional, Tuple
import netifaces
import requests
import time

logger = logging.getLogger(__name__)


class NetworkManager:
    """مدیریت عملیات شبکه‌ای"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        مقداردهی اولیه Network Manager
        
        Args:
            config: تنظیمات شبکه
        """
        self.config = config or {}
        self.timeout = self.config.get('timeout', 5)
        
        logger.info("Network Manager initialized")
    
    # ==================== Host Connectivity ====================
    
    def check_host_connectivity(self, host: str, port: int = 22, 
                               timeout: int = None) -> Dict:
        """
        بررسی اتصال به host
        
        Args:
            host: آدرس host
            port: پورت
            timeout: timeout (ثانیه)
            
        Returns:
            وضعیت اتصال
        """
        try:
            timeout = timeout or self.timeout
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            start_time = time.time()
            result = sock.connect_ex((host, port))
            end_time = time.time()
            
            sock.close()
            
            is_connected = result == 0
            latency = round((end_time - start_time) * 1000, 2)  # میلی‌ثانیه
            
            response = {
                'success': True,
                'host': host,
                'port': port,
                'connected': is_connected,
                'latency_ms': latency if is_connected else None,
                'error_code': result if not is_connected else None,
                'message': f"Connected to {host}:{port} (latency: {latency}ms)" 
                if is_connected else f"Failed to connect to {host}:{port} (error: {result})"
            }
            
            logger.debug(f"Host connectivity check: {host}:{port} - {'Connected' if is_connected else 'Failed'}")
            return response
            
        except socket.gaierror as e:
            error_msg = f"DNS resolution failed for {host}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'host': host,
                'port': port,
                'connected': False,
                'error': error_msg,
                'error_type': 'DNS resolution failed'
            }
        except Exception as e:
            error_msg = f"Error checking connectivity to {host}:{port}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'host': host,
                'port': port,
                'connected': False,
                'error': error_msg
            }
    
    def ping_host(self, host: str, count: int = 3, timeout: int = 2) -> Dict:
        """
        ping کردن host
        
        Args:
            host: آدرس host
            count: تعداد ping
            timeout: timeout برای هر ping
            
        Returns:
            نتایج ping
        """
        try:
            import platform
            
            # پارامترهای ping بر اساس سیستم عامل
            if platform.system().lower() == "windows":
                cmd = ['ping', '-n', str(count), '-w', str(timeout * 1000), host]
            else:
                cmd = ['ping', '-c', str(count), '-W', str(timeout), host]
            
            logger.debug(f"Pinging host: {host}")
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout * count + 5
            )
            
            # تجزیه خروجی ping
            output = process.stdout
            packet_loss = 100
            avg_latency = None
            
            if platform.system().lower() == "windows":
                # تجزیه خروجی Windows ping
                for line in output.split('\n'):
                    if 'Lost' in line and 'Received' in line:
                        # مثال: Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
                        parts = line.split(',')
                        for part in parts:
                            if 'Lost' in part:
                                lost = int(part.split('=')[1].strip().split()[0])
                                sent = int(parts[0].split('=')[1].strip())
                                packet_loss = (lost / sent) * 100 if sent > 0 else 100
                    
                    if 'Average' in line and 'ms' in line:
                        # مثال: Average = 12ms
                        try:
                            avg_latency = int(line.split('=')[1].strip().replace('ms', ''))
                        except:
                            pass
            else:
                # تجزیه خروجی Linux/Unix ping
                for line in output.split('\n'):
                    if 'packet loss' in line:
                        # مثال: 4 packets transmitted, 4 received, 0% packet loss, time 3003ms
                        try:
                            packet_loss = float(line.split('%')[0].split()[-1])
                        except:
                            pass
                    
                    if 'min/avg/max' in line:
                        # مثال: rtt min/avg/max/mdev = 8.123/12.456/18.789/3.210 ms
                        try:
                            latency_part = line.split('=')[1].strip()
                            avg_latency = float(latency_part.split('/')[1])
                        except:
                            pass
            
            success = process.returncode == 0 and packet_loss < 100
            
            result = {
                'success': True,
                'host': host,
                'reachable': success,
                'packet_loss_percent': packet_loss,
                'avg_latency_ms': avg_latency,
                'returncode': process.returncode,
                'output': output,
                'message': f"Host {host} is reachable (packet loss: {packet_loss}%, latency: {avg_latency}ms)"
                if success else f"Host {host} is not reachable (packet loss: {packet_loss}%)"
            }
            
            logger.debug(f"Ping results for {host}: reachable={success}, loss={packet_loss}%")
            return result
            
        except subprocess.TimeoutExpired:
            error_msg = f"Ping timeout for host {host}"
            logger.error(error_msg)
            return {
                'success': False,
                'host': host,
                'reachable': False,
                'error': error_msg,
                'timeout': True
            }
        except Exception as e:
            error_msg = f"Error pinging host {host}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'host': host,
                'reachable': False,
                'error': error_msg
            }
    
    # ==================== DNS Operations ====================
    
    def check_dns_resolution(self, domain: str, dns_server: str = None) -> Dict:
        """
        بررسی DNS resolution
        
        Args:
            domain: نام دامنه
            dns_server: DNS server (اختیاری)
            
        Returns:
            وضعیت DNS resolution
        """
        try:
            # اگر DNS server مشخص شده، از nslookup استفاده کن
            if dns_server:
                cmd = ['nslookup', domain, dns_server]
                
                process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                resolved = process.returncode == 0
                output = process.stdout
                
                if resolved:
                    # استخراج IP از خروجی nslookup
                    ips = []
                    for line in output.split('\n'):
                        if 'Address:' in line and not '#' in line:
                            ip = line.split(':')[1].strip()
                            if ip != dns_server:
                                ips.append(ip)
                    
                    ip_address = ips[0] if ips else None
                else:
                    ip_address = None
                    
            else:
                # استفاده از socket.gethostbyname
                start_time = time.time()
                ip_address = socket.gethostbyname(domain)
                end_time = time.time()
                resolved = True
                output = None
            
            result = {
                'success': True,
                'domain': domain,
                'resolved': resolved,
                'ip_address': ip_address,
                'dns_server': dns_server,
                'latency_ms': round((end_time - start_time) * 1000, 2) if resolved and not dns_server else None,
                'output': output,
                'message': f"Domain {domain} resolved to {ip_address}"
                if resolved else f"Failed to resolve domain {domain}"
            }
            
            logger.debug(f"DNS resolution for {domain}: {'Resolved' if resolved else 'Failed'} to {ip_address}")
            return result
            
        except socket.gaierror:
            error_msg = f"DNS resolution failed for domain {domain}"
            logger.debug(error_msg)
            return {
                'success': True,
                'domain': domain,
                'resolved': False,
                'error': error_msg,
                'message': error_msg
            }
        except Exception as e:
            error_msg = f"Error checking DNS resolution for {domain}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'domain': domain,
                'resolved': False,
                'error': error_msg
            }
    
    def get_dns_servers(self) -> Dict:
        """
        دریافت لیست DNS servers سیستم
        
        Returns:
            لیست DNS servers
        """
        try:
            import platform
            
            dns_servers = []
            
            if platform.system().lower() == "windows":
                # در ویندوز
                import ctypes
                import ctypes.wintypes
                
                class DNS_CACHE_ENTRY(ctypes.Structure):
                    _fields_ = [
                        ("next", ctypes.c_void_p),
                        ("name", ctypes.c_wchar_p),
                        ("data", ctypes.c_wchar_p),
                        ("type", ctypes.c_uint),
                        ("flags", ctypes.c_uint),
                        ("ttl", ctypes.c_ulong),
                    ]
                
                # این یک پیاده‌سازی ساده است
                # برای پیاده‌سازی کامل نیاز به WinAPI دارد
                dns_servers = ["8.8.8.8", "8.8.4.4"]  # مثال
                
            else:
                # در Linux/Unix
                try:
                    with open('/etc/resolv.conf', 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('nameserver'):
                                dns_server = line.split()[1]
                                dns_servers.append(dns_server)
                except FileNotFoundError:
                    pass
            
            result = {
                'success': True,
                'dns_servers': dns_servers,
                'count': len(dns_servers),
                'message': f"Found {len(dns_servers)} DNS servers"
            }
            
            logger.debug(f"DNS servers: {dns_servers}")
            return result
            
        except Exception as e:
            error_msg = f"Error getting DNS servers: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'dns_servers': []
            }
    
    # ==================== Network Interfaces ====================
    
    def get_network_interfaces(self) -> Dict:
        """
        دریافت لیست interfaceهای شبکه
        
        Returns:
            لیست interfaceها
        """
        try:
            interfaces = netifaces.interfaces()
            
            interface_details = []
            
            for interface in interfaces:
                try:
                    addrs = netifaces.ifaddresses(interface)
                    
                    # آدرس‌های IPv4
                    ipv4_addrs = []
                    if netifaces.AF_INET in addrs:
                        for addr_info in addrs[netifaces.AF_INET]:
                            ipv4_addrs.append({
                                'address': addr_info.get('addr'),
                                'netmask': addr_info.get('netmask'),
                                'broadcast': addr_info.get('broadcast')
                            })
                    
                    # آدرس‌های IPv6
                    ipv6_addrs = []
                    if netifaces.AF_INET6 in addrs:
                        for addr_info in addrs[netifaces.AF_INET6]:
                            ipv6_addrs.append({
                                'address': addr_info.get('addr'),
                                'netmask': addr_info.get('netmask')
                            })
                    
                    # MAC address
                    mac_addr = None
                    if netifaces.AF_LINK in addrs:
                        mac_addr = addrs[netifaces.AF_LINK][0].get('addr')
                    
                    interface_details.append({
                        'name': interface,
                        'mac_address': mac_addr,
                        'ipv4_addresses': ipv4_addrs,
                        'ipv6_addresses': ipv6_addrs,
                        'is_up': self._is_interface_up(interface)
                    })
                    
                except Exception as e:
                    logger.warning(f"Error getting details for interface {interface}: {str(e)}")
                    continue
            
            result = {
                'success': True,
                'interfaces': interface_details,
                'total_interfaces': len(interfaces),
                'message': f"Found {len(interfaces)} network interfaces"
            }
            
            logger.debug(f"Network interfaces: {len(interfaces)} found")
            return result
            
        except Exception as e:
            error_msg = f"Error getting network interfaces: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'interfaces': []
            }
    
    def _is_interface_up(self, interface: str) -> bool:
        """
        بررسی آیا interface فعال است
        
        Args:
            interface: نام interface
            
        Returns:
            True اگر فعال باشد
        """
        try:
            import platform
            
            if platform.system().lower() == "windows":
                # در ویندوز
                cmd = ['netsh', 'interface', 'show', 'interface', interface]
                process = subprocess.run(cmd, capture_output=True, text=True)
                return "Connected" in process.stdout
            else:
                # در Linux/Unix
                with open(f'/sys/class/net/{interface}/operstate', 'r') as f:
                    state = f.read().strip()
                return state == 'up'
                
        except Exception:
            return False
    
    def get_local_ip(self, interface: str = None) -> Dict:
        """
        دریافت IP محلی
        
        Args:
            interface: interface خاص (اختیاری)
            
        Returns:
            آدرس IP
        """
        try:
            if interface:
                # IP برای interface خاص
                interfaces = self.get_network_interfaces()
                if not interfaces['success']:
                    return interfaces
                
                for iface in interfaces['interfaces']:
                    if iface['name'] == interface:
                        ipv4_addrs = iface['ipv4_addresses']
                        if ipv4_addrs:
                            return {
                                'success': True,
                                'interface': interface,
                                'ip_address': ipv4_addrs[0]['address'],
                                'netmask': ipv4_addrs[0]['netmask'],
                                'method': 'specific_interface'
                            }
                
                return {
                    'success': False,
                    'error': f"No IPv4 address found for interface {interface}",
                    'interface': interface
                }
            else:
                # IP عمومی (با اتصال به اینترنت)
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    ip_address = s.getsockname()[0]
                    s.close()
                    
                    return {
                        'success': True,
                        'ip_address': ip_address,
                        'method': 'socket_connect',
                        'message': f"Local IP address: {ip_address}"
                    }
                    
                except Exception:
                    # روش fallback
                    hostname = socket.gethostname()
                    ip_address = socket.gethostbyname(hostname)
                    
                    return {
                        'success': True,
                        'ip_address': ip_address,
                        'hostname': hostname,
                        'method': 'hostname_resolution',
                        'message': f"Local IP address via hostname: {ip_address}"
                    }
            
        except Exception as e:
            error_msg = f"Error getting local IP: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def get_public_ip(self) -> Dict:
        """
        دریافت IP عمومی
        
        Returns:
            آدرس IP عمومی
        """
        try:
            # استفاده از سرویس‌های مختلف برای دریافت IP عمومی
            services = [
                'https://api.ipify.org',
                'https://icanhazip.com',
                'https://ident.me'
            ]
            
            for service in services:
                try:
                    response = requests.get(service, timeout=5)
                    if response.status_code == 200:
                        ip_address = response.text.strip()
                        
                        # اعتبارسنجی IP
                        if self.validate_ip_address(ip_address):
                            return {
                                'success': True,
                                'ip_address': ip_address,
                                'service': service,
                                'message': f"Public IP address: {ip_address}"
                            }
                except Exception:
                    continue
            
            error_msg = "All public IP services failed"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'services_tried': services
            }
            
        except Exception as e:
            error_msg = f"Error getting public IP: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    # ==================== Port Scanning ====================
    
    def scan_port(self, host: str, port: int, timeout: int = None) -> Dict:
        """
        اسکن یک پورت
        
        Args:
            host: آدرس host
            port: شماره پورت
            timeout: timeout
            
        Returns:
            وضعیت پورت
        """
        try:
            timeout = timeout or self.timeout
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            start_time = time.time()
            result = sock.connect_ex((host, port))
            end_time = time.time()
            
            sock.close()
            
            is_open = result == 0
            latency = round((end_time - start_time) * 1000, 2)
            
            # تشخیص سرویس احتمالی
            service = self._get_service_name(port)
            
            response = {
                'success': True,
                'host': host,
                'port': port,
                'open': is_open,
                'latency_ms': latency if is_open else None,
                'service': service,
                'error_code': result if not is_open else None,
                'message': f"Port {port} ({service}) is open on {host}" 
                if is_open else f"Port {port} is closed on {host}"
            }
            
            logger.debug(f"Port scan: {host}:{port} - {'Open' if is_open else 'Closed'}")
            return response
            
        except Exception as e:
            error_msg = f"Error scanning port {host}:{port}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'host': host,
                'port': port,
                'open': False,
                'error': error_msg
            }
    
    def scan_ports(self, host: str, ports: List[int], 
                  timeout: int = None, max_workers: int = 10) -> Dict:
        """
        اسکن چندین پورت
        
        Args:
            host: آدرس host
            ports: لیست پورت‌ها
            timeout: timeout برای هر پورت
            max_workers: حداکثر threadها
            
        Returns:
            نتایج اسکن
        """
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            timeout = timeout or self.timeout
            open_ports = []
            closed_ports = []
            errors = []
            
            logger.info(f"Scanning {len(ports)} ports on {host}")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # ارسال همه tasks
                future_to_port = {
                    executor.submit(self.scan_port, host, port, timeout): port 
                    for port in ports
                }
                
                # پردازش results
                for future in as_completed(future_to_port):
                    port = future_to_port[future]
                    try:
                        result = future.result()
                        if result['success']:
                            if result['open']:
                                open_ports.append(result)
                            else:
                                closed_ports.append(result)
                        else:
                            errors.append({
                                'port': port,
                                'error': result.get('error')
                            })
                    except Exception as e:
                        errors.append({
                            'port': port,
                            'error': str(e)
                        })
            
            result = {
                'success': True,
                'host': host,
                'total_ports': len(ports),
                'open_ports': len(open_ports),
                'closed_ports': len(closed_ports),
                'errors': len(errors),
                'open_ports_list': open_ports,
                'closed_ports_list': closed_ports,
                'errors_list': errors,
                'message': f"Scan completed: {len(open_ports)} open, {len(closed_ports)} closed, {len(errors)} errors"
            }
            
            logger.info(f"Port scan completed for {host}: {result['message']}")
            return result
            
        except Exception as e:
            error_msg = f"Error scanning ports on {host}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'host': host,
                'error': error_msg
            }
    
    def _get_service_name(self, port: int) -> str:
        """
        دریافت نام سرویس بر اساس پورت
        
        Args:
            port: شماره پورت
            
        Returns:
            نام سرویس
        """
        common_ports = {
            20: 'FTP Data',
            21: 'FTP Control',
            22: 'SSH',
            23: 'Telnet',
            25: 'SMTP',
            53: 'DNS',
            80: 'HTTP',
            110: 'POP3',
            119: 'NNTP',
            123: 'NTP',
            143: 'IMAP',
            161: 'SNMP',
            194: 'IRC',
            443: 'HTTPS',
            465: 'SMTPS',
            587: 'SMTP Submission',
            993: 'IMAPS',
            995: 'POP3S',
            3306: 'MySQL',
            3389: 'RDP',
            5432: 'PostgreSQL',
            6379: 'Redis',
            8080: 'HTTP Proxy',
            8443: 'HTTPS Alt',
            27017: 'MongoDB',
            9200: 'Elasticsearch'
        }
        
        return common_ports.get(port, 'Unknown')
    
    # ==================== IP Validation ====================
    
    def validate_ip_address(self, ip: str) -> bool:
        """
        اعتبارسنجی آدرس IP
        
        Args:
            ip: آدرس IP
            
        Returns:
            True اگر معتبر باشد
        """
        try:
            # IPv4
            try:
                ipaddress.IPv4Address(ip)
                return True
            except ipaddress.AddressValueError:
                pass
            
            # IPv6
            try:
                ipaddress.IPv6Address(ip)
                return True
            except ipaddress.AddressValueError:
                pass
            
            return False
            
        except Exception:
            return False
    
    def validate_cidr(self, cidr: str) -> bool:
        """
        اعتبارسنجی CIDR notation
        
        Args:
            cidr: CIDR (مثلا 192.168.1.0/24)
            
        Returns:
            True اگر معتبر باشد
        """
        try:
            ipaddress.ip_network(cidr, strict=False)
            return True
        except ValueError:
            return False
    
    def get_network_info(self, ip: str, netmask: str = None) -> Dict:
        """
        دریافت اطلاعات شبکه از IP و netmask
        
        Args:
            ip: آدرس IP
            netmask: subnet mask (اختیاری)
            
        Returns:
            اطلاعات شبکه
        """
        try:
            if not self.validate_ip_address(ip):
                return {
                    'success': False,
                    'error': f"Invalid IP address: {ip}",
                    'ip': ip
                }
            
            if netmask:
                # استفاده از IP و netmask
                if not self.validate_ip_address(netmask):
                    return {
                        'success': False,
                        'error': f"Invalid netmask: {netmask}",
                        'ip': ip,
                        'netmask': netmask
                    }
                
                # ساخت CIDR از IP و netmask
                network = ipaddress.ip_network(f"{ip}/{netmask}", strict=False)
            else:
                # فرض /24 برای IPv4 و /64 برای IPv6
                if ':' in ip:  # IPv6
                    network = ipaddress.ip_network(f"{ip}/64", strict=False)
                else:  # IPv4
                    network = ipaddress.ip_network(f"{ip}/24", strict=False)
            
            info = {
                'success': True,
                'ip': ip,
                'network': str(network.network_address),
                'netmask': str(network.netmask),
                'broadcast': str(network.broadcast_address) if network.version == 4 else None,
                'cidr': f"{network.network_address}/{network.prefixlen}",
                'prefix_length': network.prefixlen,
                'num_addresses': network.num_addresses,
                'usable_hosts': network.num_addresses - 2 if network.version == 4 else network.num_addresses,
                'version': network.version,  # 4 برای IPv4، 6 برای IPv6
                'is_private': network.is_private,
                'is_global': network.is_global,
                'is_multicast': network.is_multicast,
                'is_reserved': network.is_reserved
            }
            
            logger.debug(f"Network info for {ip}: {info['cidr']}")
            return info
            
        except Exception as e:
            error_msg = f"Error getting network info for {ip}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'ip': ip
            }
    
    # ==================== HTTP/HTTPS Testing ====================
    
    def test_http_endpoint(self, url: str, timeout: int = 10, 
                          verify_ssl: bool = True) -> Dict:
        """
        تست endpoint HTTP/HTTPS
        
        Args:
            url: URL
            timeout: timeout
            verify_ssl: اعتبارسنجی SSL
            
        Returns:
            نتیجه تست
        """
        try:
            start_time = time.time()
            response = requests.get(
                url, 
                timeout=timeout, 
                verify=verify_ssl,
                allow_redirects=True
            )
            end_time = time.time()
            
            response_time = round((end_time - start_time) * 1000, 2)
            
            result = {
                'success': True,
                'url': url,
                'status_code': response.status_code,
                'status_ok': 200 <= response.status_code < 300,
                'response_time_ms': response_time,
                'content_length': len(response.content),
                'content_type': response.headers.get('Content-Type'),
                'server': response.headers.get('Server'),
                'redirects': len(response.history) if hasattr(response, 'history') else 0,
                'final_url': response.url,
                'message': f"HTTP {response.status_code} - {response.reason} ({response_time}ms)"
            }
            
            logger.debug(f"HTTP test for {url}: Status {response.status_code}, Time {response_time}ms")
            return result
            
        except requests.exceptions.SSLError as e:
            error_msg = f"SSL error for {url}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'url': url,
                'error': error_msg,
                'error_type': 'SSL Error'
            }
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout for {url}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'url': url,
                'error': error_msg,
                'error_type': 'Timeout'
            }
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error for {url}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'url': url,
                'error': error_msg,
                'error_type': 'Connection Error'
            }
        except Exception as e:
            error_msg = f"Error testing HTTP endpoint {url}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'url': url,
                'error': error_msg
            }
    
    # ==================== Bandwidth Testing ====================
    
    def test_bandwidth(self, url: str = None, size_mb: int = 10, 
                      timeout: int = 30) -> Dict:
        """
        تست پهنای باند (دانلود)
        
        Args:
            url: URL فایل برای دانلود (اگر None باشد از فایل تست استفاده می‌شود)
            size_mb: سایز فایل تست (مگابایت)
            timeout: timeout کل
        
        Returns:
            نتایج تست پهنای باند
        """
        try:
            if url is None:
                # استفاده از فایل تست
                url = f"http://speedtest.ftp.otenet.gr/files/test{size_mb}Mb.db"
            
            logger.info(f"Testing bandwidth with {url}")
            
            start_time = time.time()
            response = requests.get(url, stream=True, timeout=timeout)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f"Failed to download test file: HTTP {response.status_code}",
                    'url': url,
                    'status_code': response.status_code
                }
            
            # دانلود فایل و محاسبه سرعت
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 1024 * 1024  # 1MB chunks
            
            # خواندن داده‌ها
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    downloaded += len(chunk)
            
            end_time = time.time()
            download_time = end_time - start_time
            
            if download_time == 0:
                download_time = 0.001  # جلوگیری از تقسیم بر صفر
            
            # محاسبه سرعت
            speed_bps = downloaded / download_time
            speed_mbps = speed_bps / 1_000_000
            speed_mb_per_s = downloaded / download_time / 1_048_576  # MB/s
            
            result = {
                'success': True,
                'url': url,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / 1_048_576,
                'downloaded_bytes': downloaded,
                'download_time_seconds': round(download_time, 2),
                'speed_bps': round(speed_bps, 2),
                'speed_kbps': round(speed_bps / 1000, 2),
                'speed_mbps': round(speed_mbps, 2),
                'speed_mb_per_s': round(speed_mb_per_s, 2),
                'message': f"Bandwidth test: {round(speed_mbps, 2)} Mbps ({round(speed_mb_per_s, 2)} MB/s)"
            }
            
            logger.info(f"Bandwidth test completed: {result['message']}")
            return result
            
        except Exception as e:
            error_msg = f"Error testing bandwidth: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'url': url
            }


def create_network_manager(config: Dict = None) -> NetworkManager:
    """
    تابع helper برای ایجاد Network Manager
    
    Args:
        config: تنظیمات
        
    Returns:
        instance از NetworkManager
    """
    return NetworkManager(config)