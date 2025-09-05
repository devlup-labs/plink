import socket
import struct
import random
import time
import subprocess
import platform
import json
import requests
from concurrent.futures import ThreadPoolExecutor
import sys
import os

class NetworkAnalyzer:
    def __init__(self):
        self.results = {
            'network_type': None,
            'nat_type': None,
            'nat_detection_details': {},
            'upnp_enabled': False,
            'external_ip': None,
            'local_ip': None,
            'open_ports': [],
            'firewall_blocks': [],
            'stun_results': [],
            'connection_test': {},
            'recommendations': [],
            'firewall_info': {}
        }

        def fetch_stun_servers(url):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                lines = response.text.strip().split('\n')
                stun_servers = []
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if ':' in line:
                        host, port = line.split(':', 1)
                        host = host.strip()
                        try:
                            port = int(port.strip())
                        except ValueError:
                            continue
                        stun_servers.append((host, port))
                return stun_servers
            except Exception as e:
                print(f"Error fetching STUN servers: {e}")
                return []

        url = "https://raw.githubusercontent.com/pradt2/always-online-stun/master/valid_hosts.txt"
        self.stun_servers = fetch_stun_servers(url)

        # Fallback STUN servers if the list fails to load
        if not self.stun_servers:
            self.stun_servers = [
                ('stun.l.google.com', 19302),
                ('stun1.l.google.com', 19302),
                ('stun2.l.google.com', 19302),
                ('stun.services.mozilla.com', 3478),
                ('stun.stunprotocol.org', 3478)
            ]

        # common ports to test
        self.test_ports = [80, 443, 22, 21, 25, 53, 110, 143, 993, 995, 3389, 5060, 8080, 8443]

        # find 64 open ports for the app
        self.target_open_ports = 64
        self.found_open_ports = []

    def get_local_ip(self):
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            self.results['local_ip'] = local_ip
            return local_ip
        except Exception as e:
            print(f"Error getting local IP: {e}")
            return None

    def stun_request(self, server, port, local_port=0):
        """Send STUN Binding Request and parse XOR-MAPPED-ADDRESS (RFC 5389)"""
        MAGIC_COOKIE = 0x2112A442
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('0.0.0.0', local_port))
            sock.settimeout(2)

            # Build STUN Binding Request
            trans_id = os.urandom(12)  # secure 12-byte transaction ID
            msg_type = 0x0001  # Binding request
            msg_len = 0
            magic_cookie_bytes = MAGIC_COOKIE.to_bytes(4, 'big')
            header = struct.pack('!HH4s12s', msg_type, msg_len, magic_cookie_bytes, trans_id)

            sock.sendto(header, (server, port))
            data, _ = sock.recvfrom(2048)

            if len(data) < 20:
                return {'success': False, 'error': 'Short STUN response'}

            r_msg_type, r_msg_len, r_magic_cookie = struct.unpack('!HH4s', data[:8])
            # r_trans_id = data[8:20]

            if r_msg_type != 0x0101:  # Binding Success Response
                return {'success': False, 'error': f'Invalid STUN response type: {hex(r_msg_type)}'}

            i = 20
            end = 20 + r_msg_len
            # Ensure we don't read past actual packet length
            end = min(end, len(data))

            external_ip = None
            external_port = None

            while i + 4 <= end:
                attr_type, attr_len = struct.unpack('!HH', data[i:i+4])
                i += 4
                if i + attr_len > len(data):
                    break
                attr_value = data[i:i+attr_len]

                # XOR-MAPPED-ADDRESS (0x0020)
                if attr_type == 0x0020 and attr_len >= 8:
                    family = attr_value[1]
                    xport = struct.unpack('!H', attr_value[2:4])[0]
                    xport ^= (MAGIC_COOKIE >> 16) & 0xFFFF  # XOR with 0x2112
                    if family == 0x01 and attr_len >= 8:  # IPv4
                        xip_int = struct.unpack('!I', attr_value[4:8])[0]
                        ip_int = xip_int ^ MAGIC_COOKIE
                        external_ip = socket.inet_ntoa(struct.pack('!I', ip_int))
                        external_port = xport
                        break
                    # (Skipping IPv6 case for brevity)

                # 32-bit padding
                i += (attr_len + 3) & ~3

            local_used = sock.getsockname()[1]
            sock.close()

            if external_ip and external_port:
                return {
                    'success': True,
                    'external_ip': external_ip,
                    'external_port': external_port,
                    'local_port': local_used,
                    'server': server,
                    'server_port': port
                }
            else:
                return {'success': False, 'error': 'No XOR-MAPPED-ADDRESS found'}

        except socket.timeout:
            return {'success': False, 'error': 'Timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def detect_nat_type(self):
        """Detect NAT type using STUN with proper analysis"""
        print("Detecting NAT type...")

        detection_details = {
            'test_results': [],
            'analysis': [],
            'reasoning': []
        }

        # Test 1: Basic STUN request to first server
        print("  Test 1: Basic STUN request...")
        first_result = None
        for server, port in self.stun_servers:
            result = self.stun_request(server, port)
            if result.get('success'):
                first_result = result
                break

        if not first_result:
            self.results['nat_type'] = 'Unknown (STUN failed)'
            self.results['nat_detection_details'] = {'error': 'All STUN servers failed'}
            return

        detection_details['test_results'].append({
            'test': 'Test 1 - Basic STUN',
            'server': first_result['server'],
            'server_port': first_result['server_port'],
            'local_port': first_result['local_port'],
            'external_ip': first_result['external_ip'],
            'external_port': first_result['external_port'],
            'success': True
        })

        self.results['external_ip'] = first_result['external_ip']
        local_ip = self.get_local_ip()

        detection_details['analysis'].append(f"Local IP: {local_ip}")
        detection_details['analysis'].append(f"External IP: {first_result['external_ip']}")

        # Check if behind NAT
        if first_result['external_ip'] == local_ip:
            self.results['network_type'] = 'Direct Internet Connection'
            self.results['nat_type'] = 'No NAT'
            detection_details['reasoning'].append("External IP matches local IP - No NAT detected")
            self.results['nat_detection_details'] = detection_details
            return

        self.results['network_type'] = 'Behind NAT'
        detection_details['reasoning'].append("External IP differs from local IP - Behind NAT")

        # Test 2: Same local port, different STUN server
        print("  Test 2: Same local port, different server...")
        second_result = None
        for server, port in self.stun_servers[1:]:
            if server != first_result['server']:
                result = self.stun_request(server, port, first_result['local_port'])
                if result.get('success'):
                    second_result = result
                    break

        if not second_result:
            self.results['nat_type'] = 'Unknown (Second STUN test failed)'
            detection_details['reasoning'].append("Second STUN test failed - Cannot determine NAT type")
            self.results['nat_detection_details'] = detection_details
            return

        detection_details['test_results'].append({
            'test': 'Test 2 - Same local port, different server',
            'server': second_result['server'],
            'server_port': second_result['server_port'],
            'local_port': second_result['local_port'],
            'external_ip': second_result['external_ip'],
            'external_port': second_result['external_port'],
            'success': True
        })

        # Test 3: Same server, different server port (if available)
        print("  Test 3: Same server, different server port...")
        third_result = None
        for server, port in self.stun_servers:
            if server == first_result['server'] and port != first_result['server_port']:
                result = self.stun_request(server, port, first_result['local_port'])
                if result.get('success'):
                    third_result = result
                    break

        if third_result:
            detection_details['test_results'].append({
                'test': 'Test 3 - Same server, different server port',
                'server': third_result['server'],
                'server_port': third_result['server_port'],
                'local_port': third_result['local_port'],
                'external_ip': third_result['external_ip'],
                'external_port': third_result['external_port'],
                'success': True
            })

        # Test 4: Different local port, same server
        print("  Test 4: Different local port, same server...")
        fourth_result = self.stun_request(first_result['server'], first_result['server_port'])
        if fourth_result and fourth_result.get('success'):
            detection_details['test_results'].append({
                'test': 'Test 4 - Different local port, same server',
                'server': fourth_result['server'],
                'server_port': fourth_result['server_port'],
                'local_port': fourth_result['local_port'],
                'external_ip': fourth_result['external_ip'],
                'external_port': fourth_result['external_port'],
                'success': True
            })

        # NAT Type Analysis
        print("  Analyzing NAT behavior...")

        # Compare IP addresses/ports
        same_external_ip = first_result['external_ip'] == second_result['external_ip']
        same_external_port = first_result['external_port'] == second_result['external_port']

        detection_details['analysis'].append("Test 1 vs Test 2:")
        detection_details['analysis'].append(f"  External IP same: {same_external_ip} ({first_result['external_ip']} vs {second_result['external_ip']})")
        detection_details['analysis'].append(f"  External Port same: {same_external_port} ({first_result['external_port']} vs {second_result['external_port']})")

        if same_external_ip and same_external_port:
            detection_details['reasoning'].append("Same external IP:Port from different servers - Indicates cone NAT")

            if third_result and third_result.get('success'):
                same_port_diff_server_port = first_result['external_port'] == third_result['external_port']
                detection_details['analysis'].append("Test 1 vs Test 3 (different server port):")
                detection_details['analysis'].append(f"  External Port same: {same_port_diff_server_port} ({first_result['external_port']} vs {third_result['external_port']})")

                if same_port_diff_server_port:
                    self.results['nat_type'] = 'Full Cone NAT'
                    detection_details['reasoning'].append("Same external port even with different server port - Full Cone NAT")
                else:
                    self.results['nat_type'] = 'Port Restricted Cone NAT'
                    detection_details['reasoning'].append("Different external port with different server port - Port Restricted Cone NAT")
            else:
                if fourth_result and fourth_result.get('success'):
                    diff_local_same_external = first_result['external_port'] != fourth_result['external_port']
                    detection_details['analysis'].append("Test 1 vs Test 4 (different local port):")
                    detection_details['analysis'].append(f"  External Port different: {diff_local_same_external} ({first_result['external_port']} vs {fourth_result['external_port']})")

                    if diff_local_same_external:
                        self.results['nat_type'] = 'Port Restricted Cone NAT'
                        detection_details['reasoning'].append("Different local port gives different external port - Port Restricted Cone NAT")
                    else:
                        self.results['nat_type'] = 'Restricted Cone NAT'
                        detection_details['reasoning'].append("Same external mapping regardless of local port - Restricted Cone NAT")
                else:
                    self.results['nat_type'] = 'Restricted Cone NAT'
                    detection_details['reasoning'].append("Assuming Restricted Cone NAT (insufficient test data)")

        elif same_external_ip and not same_external_port:
            self.results['nat_type'] = 'Port Restricted Cone NAT'
            detection_details['reasoning'].append("Same external IP but different ports from different servers - Port Restricted Cone NAT")

        elif not same_external_ip:
            self.results['nat_type'] = 'Symmetric NAT'
            detection_details['reasoning'].append("Different external IP from different servers - Symmetric NAT")
        else:
            self.results['nat_type'] = 'Unknown NAT Type'
            detection_details['reasoning'].append("Unable to determine NAT type from test results")

        # Store all STUN results for reference
        self.results['stun_results'] = [r for r in [first_result, second_result, third_result, fourth_result] if r and r.get('success')]
        self.results['nat_detection_details'] = detection_details

    def check_upnp(self):
        """Check if UPnP is available via SSDP M-SEARCH"""
        print("Checking UPnP availability...")

        msg = (
            'M-SEARCH * HTTP/1.1\r\n'
            'HOST: 239.255.255.250:1900\r\n'
            'MAN: "ssdp:discover"\r\n'
            'ST: upnp:rootdevice\r\n'
            'MX: 2\r\n\r\n'
        ).encode()

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)
            # Try a few times; some devices are finicky
            found = False
            for _ in range(3):
                sock.sendto(msg, ('239.255.255.250', 1900))
                try:
                    data, _ = sock.recvfrom(2048)
                    if b'HTTP/1.1 200 OK' in data:
                        found = True
                        break
                except socket.timeout:
                    continue
            self.results['upnp_enabled'] = found
            print("UPnP is available" if found else "UPnP not available")
            sock.close()
        except Exception as e:
            self.results['upnp_enabled'] = False
            print(f"UPnP check failed: {e}")

    def test_port_connectivity(self, port, timeout=2):
        """Test if outbound TCP connection is possible to a well-known host on a given port."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex(('google.com', port))
            sock.close()

            if result == 0:
                return {'port': port, 'status': 'open', 'direction': 'outbound'}
            else:
                return {'port': port, 'status': 'blocked', 'direction': 'outbound'}
        except Exception as e:
            return {'port': port, 'status': 'error', 'direction': 'outbound', 'error': str(e)}

    def test_inbound_port(self, port):
        """Test if inbound connections are possible on a port (bindable == available locally)"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', port))
            sock.listen(1)
            sock.settimeout(0.5)
            sock.close()
            return {'port': port, 'status': 'bindable', 'direction': 'inbound'}
        except socket.error as e:
            # errno may differ by platform; keep generic mapping
            if hasattr(e, 'errno') and e.errno in (98, 48, 10048):  # in use (Linux/Mac/Win)
                return {'port': port, 'status': 'in_use', 'direction': 'inbound'}
            elif hasattr(e, 'errno') and e.errno in (13, 1):  # permission denied
                return {'port': port, 'status': 'permission_denied', 'direction': 'inbound'}
            else:
                return {'port': port, 'status': 'blocked', 'direction': 'inbound', 'error': str(e)}
        except Exception as e:
            return {'port': port, 'status': 'blocked', 'direction': 'inbound', 'error': str(e)}

    def find_open_ports(self):
        """Find 64 open/bindable ports for the app"""
        print(f"Finding {self.target_open_ports} open ports")

        # Outbound checks
        print("Testing outbound connectivity on common ports...")
        with ThreadPoolExecutor(max_workers=20) as executor:
            outbound_futures = [executor.submit(self.test_port_connectivity, port) for port in self.test_ports]
            for future in outbound_futures:
                result = future.result()
                if result['status'] == 'open':
                    self.found_open_ports.append(result)
                    self.results['open_ports'].append(result)
                elif result['status'] == 'blocked':
                    self.results['firewall_blocks'].append(result)

        print(f"Found {len([p for p in self.found_open_ports if p['direction']=='outbound'])} open outbound ports")

        # Inbound (bindable) ports
        print("Finding available inbound ports...")
        port_ranges = [
            (8000, 9000),
            (10000, 11000),
            (12000, 13000),
            (20000, 21000),
            (30000, 31000),
            (40000, 41000),
            (50000, 51000),
            (60000, 61000),
        ]

        for start_port, end_port in port_ranges:
            if len(self.found_open_ports) >= self.target_open_ports:
                break

            print(f"  Scanning range {start_port}-{end_port}...")

            batch_size = 100
            for batch_start in range(start_port, end_port, batch_size):
                if len(self.found_open_ports) >= self.target_open_ports:
                    break
                batch_end = min(batch_start + batch_size, end_port)

                with ThreadPoolExecutor(max_workers=32) as executor:
                    futures = [executor.submit(self.test_inbound_port, port)
                               for port in range(batch_start, batch_end)]

                    for future in futures:
                        if len(self.found_open_ports) >= self.target_open_ports:
                            break

                        result = future.result()
                        if result['status'] == 'bindable':
                            self.found_open_ports.append(result)
                            self.results['open_ports'].append(result)
                            if len(self.found_open_ports) % 10 == 0:
                                print(f"Found {len(self.found_open_ports)} open/bindable ports so far...")
                        elif result['status'] == 'blocked':
                            self.results['firewall_blocks'].append(result)

        # If still short, try random high ports
        if len(self.found_open_ports) < self.target_open_ports:
            remaining = self.target_open_ports - len(self.found_open_ports)
            print(f"Trying {remaining} random high ports...")

            tested_ports = set(p['port'] for p in self.found_open_ports if 'port' in p)
            random_ports = []
            while len(random_ports) < remaining * 3:
                port = random.randint(49152, 65535)
                if port not in tested_ports:
                    random_ports.append(port)
                    tested_ports.add(port)

            with ThreadPoolExecutor(max_workers=32) as executor:
                futures = [executor.submit(self.test_inbound_port, port) for port in random_ports]
                for future in futures:
                    if len(self.found_open_ports) >= self.target_open_ports:
                        break
                    result = future.result()
                    if result['status'] == 'bindable':
                        self.found_open_ports.append(result)
                        self.results['open_ports'].append(result)
                        if len(self.found_open_ports) % 5 == 0:
                            print(f"Found {len(self.found_open_ports)} open/bindable ports total...")

        self.results['app_ports'] = {
            'total_found': len(self.found_open_ports),
            'target': self.target_open_ports,
            'success': len(self.found_open_ports) >= self.target_open_ports,
            'outbound_ports': [p['port'] for p in self.found_open_ports if p['direction'] == 'outbound'],
            'inbound_ports': [p['port'] for p in self.found_open_ports if p['direction'] == 'inbound'],
            'recommended_ports': [p['port'] for p in self.found_open_ports[:self.target_open_ports]]
        }

        print("\nPort Discovery Complete!")
        print(f"Target: {self.target_open_ports} ports")
        print(f"Found: {len(self.found_open_ports)} ports")
        print(f"Success: {'True' if len(self.found_open_ports) >= self.target_open_ports else 'False'}")

    def scan_ports(self):
        self.find_open_ports()

    def check_firewall_status(self):
        """Check system firewall status (best-effort, no sudo)"""
        print("Checking firewall status...")

        system = platform.system().lower()
        fw_info = {}

        try:
            if system == 'linux':
                # iptables (may require root for full info)
                try:
                    result = subprocess.run(['iptables', '-L'],
                                            capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        fw_info['type'] = 'iptables'
                        fw_info['active'] = ('DROP' in result.stdout) or ('REJECT' in result.stdout)
                        fw_info['rules_count'] = len(result.stdout.splitlines())
                    else:
                        fw_info['type'] = 'iptables'
                        fw_info['error'] = 'iptables not accessible (non-zero exit)'
                except Exception as e:
                    fw_info['type'] = 'iptables'
                    fw_info['error'] = str(e)

                # ufw
                try:
                    result = subprocess.run(['ufw', 'status'],
                                            capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        fw_info['ufw_status'] = result.stdout.strip()
                except Exception:
                    pass

            elif system == 'windows':
                try:
                    result = subprocess.run(['netsh', 'advfirewall', 'show', 'allprofiles', 'state'],
                                            capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        fw_info['type'] = 'windows_firewall'
                        fw_info['status'] = result.stdout
                        fw_info['active'] = ('ON' in result.stdout.upper())
                except Exception as e:
                    fw_info['type'] = 'windows_firewall'
                    fw_info['error'] = str(e)

            elif system == 'darwin':  # macOS (pf)
                try:
                    result = subprocess.run(['pfctl', '-s', 'info'],
                                            capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        fw_info['type'] = 'pf'
                        fw_info['status'] = result.stdout
                        # pfctl -s info includes "Status: Enabled/Disabled"
                        fw_info['active'] = ('Status: Enabled' in result.stdout)
                    else:
                        fw_info['type'] = 'pf'
                        fw_info['error'] = 'pfctl not accessible (non-zero exit)'
                except Exception as e:
                    fw_info['type'] = 'pf'
                    fw_info['error'] = str(e)

        except subprocess.TimeoutExpired:
            fw_info = {'error': 'Firewall check timed out'}
        except Exception as e:
            fw_info = {'error': str(e)}

        self.results['firewall_info'] = fw_info

    def test_external_connectivity(self):
        """Test external connectivity and get public IP"""
        print("Testing external connectivity...")

        services = [
            'https://httpbin.org/ip',
            'https://icanhazip.com',
            'https://ipecho.net/plain',
            'https://ident.me'
        ]

        for service in services:
            try:
                response = requests.get(service, timeout=5)
                if response.status_code == 200:
                    if 'httpbin' in service:
                        ip = response.json().get('origin', '').split(',')[0].strip()
                    else:
                        ip = response.text.strip()
                    if ip and '.' in ip:
                        self.results['external_ip_http'] = ip
                        self.results['connection_test'][service] = 'success'
                        break
                    else:
                        self.results['connection_test'][service] = 'invalid_response'
                else:
                    self.results['connection_test'][service] = f'http_{response.status_code}'
            except requests.RequestException as e:
                self.results['connection_test'][service] = f'error_{str(e)}'

    def generate_recommendations(self):
        """Generate recommendations based on analysis"""
        recommendations = []

        nat_type = self.results.get('nat_type', '') or ''

        if 'Symmetric NAT' in nat_type:
            recommendations.append("Symmetric NAT detected - P2P connections will be very difficult")
            recommendations.append("Consider using a TURN server or VPN for reliable P2P connectivity")
            recommendations.append("Try multiple connection attempts with port prediction")
        elif 'Port Restricted' in nat_type:
            recommendations.append("Port Restricted Cone NAT - P2P connections may be challenging")
            recommendations.append("Use multiple simultaneous connection attempts")
            recommendations.append("Try birthday paradox and sequential port strategies")
        elif 'Restricted Cone' in nat_type:
            recommendations.append("Restricted Cone NAT - P2P connections should work with proper hole punching")
            recommendations.append("Basic hole punching techniques should be sufficient")
        elif 'Full Cone' in nat_type:
            recommendations.append("Full Cone NAT - P2P connections should work easily")
            recommendations.append("Simple hole punching will work reliably")

        if self.results.get('upnp_enabled'):
            recommendations.append("UPnP is available - can automatically configure port forwarding")
            recommendations.append("Use UPnP for automatic port mapping when possible")
        else:
            recommendations.append("UPnP not available - manual port forwarding required")

        blocked_count = len(self.results.get('firewall_blocks', []))
        if blocked_count > 5:
            recommendations.append(f"{blocked_count} ports appear to be blocked by firewall")
            recommendations.append("Consider configuring firewall rules for your application")

        open_count = len(self.results.get('open_ports', []))
        if open_count >= self.target_open_ports:
            recommendations.append(f"Found {open_count} open ports - sufficient for your app")
        elif open_count > 0:
            recommendations.append(f"Found {open_count} open ports - may need more for optimal performance")
        else:
            recommendations.append("No ports appear to be accessible - check firewall configuration")

        # App-specific recommendations
        if 'app_ports' in self.results:
            app_ports = self.results['app_ports']
            if app_ports['success']:
                recommendations.append(f"Successfully found {app_ports['total_found']} ports for your app")
                recommendations.append("Use the recommended ports list for optimal P2P performance")
            else:
                recommendations.append(f"Only found {app_ports['total_found']}/{app_ports['target']} required ports")
                recommendations.append("Consider adjusting firewall settings or using VPN")

            outbound_count = len(app_ports['outbound_ports'])
            inbound_count = len(app_ports['inbound_ports'])

            if outbound_count > 0:
                recommendations.append(f"{outbound_count} outbound ports available for connections")
            if inbound_count > 0:
                recommendations.append(f"{inbound_count} inbound ports available for listening")

            if inbound_count < 10 and outbound_count > 0:
                recommendations.append("Consider using outbound connections primarily due to limited inbound ports")

        self.results['recommendations'] = recommendations

    def run_analysis(self):
        """Run complete network analysis"""
        print("Starting comprehensive network analysis...")
        print("=" * 50)

        # Get local IP
        self.get_local_ip()

        # Detect NAT type
        self.detect_nat_type()

        # Check UPnP
        self.check_upnp()

        # Test external connectivity
        self.test_external_connectivity()

        # Scan ports
        self.scan_ports()

        # Check firewall
        self.check_firewall_status()

        # Generate recommendations
        self.generate_recommendations()

        print("\n" + "=" * 50)
        print("Analysis complete!")

        return self.results

    def print_results(self):
        """Verbose, formatted results"""
        print("\nNETWORK ANALYSIS RESULTS")
        print("=" * 50)

        print(f"Network Type: {self.results.get('network_type', 'Unknown')}")
        print(f"NAT Type: {self.results.get('nat_type', 'Unknown')}")

        print(f"Local IP: {self.results.get('local_ip', 'Unknown')}")
        print(f"External IP (STUN): {self.results.get('external_ip', 'Unknown')}")
        if self.results.get('external_ip_http'):
            print(f"External IP (HTTP): {self.results.get('external_ip_http', 'Unknown')}")

        upnp_status = "Enabled" if self.results.get('upnp_enabled') else "Disabled"
        print(f"UPnP Status: {upnp_status}")

        if 'nat_detection_details' in self.results:
            details = self.results['nat_detection_details']
            print(f"\nNAT DETECTION ANALYSIS:")
            print("-" * 40)

            if 'test_results' in details:
                for test_result in details['test_results']:
                    print(f"Test: {test_result['test']}")
                    print(f"  Server: {test_result['server']}:{test_result['server_port']}")
                    print(f"  Local Port: {test_result['local_port']}")
                    print(f"  External: {test_result['external_ip']}:{test_result['external_port']}")
                    print()

            if 'analysis' in details:
                print("Analysis Details:")
                for analysis in details['analysis']:
                    print(f"  {analysis}")
                print()

            if 'reasoning' in details:
                print("NAT Type Reasoning:")
                for reason in details['reasoning']:
                    print(f"  {reason}")

        if 'app_ports' in self.results:
            app_ports = self.results['app_ports']
            print(f"\nAPP PORT DISCOVERY:")
            print("-" * 30)
            print(f"Target Ports: {app_ports['target']}")
            print(f"Found Ports: {app_ports['total_found']}")
            print(f"Success: {app_ports['success']}")
            print(f"Outbound Ports: {len(app_ports['outbound_ports'])}")
            print(f"Inbound Ports: {len(app_ports['inbound_ports'])}")

            if app_ports['recommended_ports']:
                print(f"\nRECOMMENDED PORTS FOR YOUR APP:")
                print("-" * 40)
                ports_per_line = 8
                rec_ports = app_ports['recommended_ports']
                for i in range(0, len(rec_ports), ports_per_line):
                    line_ports = rec_ports[i:i+ports_per_line]
                    print("  " + ", ".join(map(str, line_ports)))

        open_ports = len(self.results.get('open_ports', []))
        blocked_ports = len(self.results.get('firewall_blocks', []))
        print(f"\nTotal Open/Bindable Entries: {open_ports}")
        print(f"Total Blocked Entries: {blocked_ports}")

        if 'firewall_info' in self.results:
            fw_info = self.results['firewall_info']
            if 'error' not in fw_info:
                print(f"Firewall Type: {fw_info.get('type', 'Unknown')}")
                if 'active' in fw_info:
                    print(f"Firewall Active: {fw_info['active']}")
            else:
                print(f"Firewall: {fw_info['error']}")

        print(f"\nRECOMMENDATIONS:")
        print("-" * 30)
        for rec in self.results.get('recommendations', []):
            print(f"  {rec}")

        if self.results.get('open_ports'):
            outbound_ports = [p for p in self.results['open_ports'] if p['direction'] == 'outbound']
            inbound_ports = [p for p in self.results['open_ports'] if p['direction'] == 'inbound']

            if outbound_ports:
                print(f"\nOUTBOUND PORTS ({len(outbound_ports)}):")
                print("-" * 30)
                outbound_port_nums = [str(p['port']) for p in outbound_ports[:20]]
                print("  " + ", ".join(outbound_port_nums))
                if len(outbound_ports) > 20:
                    print(f"  ... and {len(outbound_ports) - 20} more")

            if inbound_ports:
                print(f"\nINBOUND (BINDABLE) PORTS ({len(inbound_ports)}):")
                print("-" * 30)
                inbound_port_nums = [str(p['port']) for p in inbound_ports[:20]]
                print("  " + ", ".join(inbound_port_nums))
                if len(inbound_ports) > 20:
                    print(f"  ... and {len(inbound_ports) - 20} more")

        if self.results.get('firewall_blocks'):
            print(f"\nSAMPLE BLOCKED/ERROR ENTRIES:")
            print("-" * 30)
            blocked_sample = self.results['firewall_blocks'][:10]
            for port_info in blocked_sample:
                print(f"  Port {port_info['port']}: {port_info['status']} ({port_info['direction']})")
            if len(self.results['firewall_blocks']) > 10:
                print(f"  ... and {len(self.results['firewall_blocks']) - 10} more")

    def export_results(self, filename=None):
        """Export results to JSON file"""
        if not filename:
            filename = f"network_analysis_{int(time.time())}.json"

        try:
            with open(filename, 'w') as f:
                json.dump(self.results, f, indent=2)

            print(f"\nResults exported to: {filename}")
            return filename

        except Exception as e:
            print(f"\nError exporting results: {e}")
            return None

    def analyze_network(self):
        """Return a flat dictionary with simplified network diagnostics"""
        self.run_analysis()
        self.export_results("network_details.json")
        return {
            "network_type": self.results.get("network_type", "Unknown"),
            "nat_type": self.results.get("nat_type", "Unknown"),
            "upnp_enabled": bool(self.results.get("upnp_enabled", False)),
            "external_ip": self.results.get("external_ip") or self.results.get("external_ip_http"),
            "local_ip": self.results.get("local_ip"),
            "firewall_enabled": bool(self.results.get("firewall_info", {}).get("active", False) or self.results.get("firewall_blocks")),
            "open_ports": [p["port"] for p in self.results.get("open_ports", []) if "port" in p][:64]
        }
