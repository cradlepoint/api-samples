#!/usr/bin/env python3
"""
Cisco Router to Cradlepoint Zone Firewall Converter v3

This script accurately converts Cisco router configurations to Cradlepoint 
zone firewall configurations with proper identity mapping:
- Object groups → Identities (IP and Port)
- Filter policy rules reference identity UUIDs
- Proper mapping between Cisco object groups and Cradlepoint identities

Author: AI Assistant
Date: 2024
"""

import json
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple
import ipaddress


class CiscoToCradlepointConverter:
    """Main converter class for Cisco to Cradlepoint zone firewall configuration."""
    
    def __init__(self, config_file: str, add_internet_zone: bool = False, internet_zone_name: str = "EXT-Internet"):
        """Initialize the converter with a Cisco configuration file."""
        self.config_file = config_file
        self.config_lines = []
        self.zones = {}
        self.zone_forwardings = {}
        self.filter_policies = {}
        self.interfaces = {}
        self.acls = {}
        self.class_maps = {}
        self.object_groups = {}
        self.policy_maps = {}
        self.zone_pairs = {}
        self.identities = {'ip': [], 'port': [], 'mac': []}
        self.add_internet_zone = add_internet_zone
        self.internet_zone_name = internet_zone_name
        
        # Protocol mappings
        self.protocol_map = {
            'icmp': [{'identity': 1}],
            'tcp': [{'identity': 6}],
            'udp': [{'identity': 17}],
            'gre': [{'identity': 47}],
            'esp': [{'identity': 50}],
            'ah': [{'identity': 51}],
            'ospf': [{'identity': 89}],
            'ip': []  # Any protocol
        }
        
        # Port mappings for common services
        self.port_map = {
            'http': 80,
            'https': 443,
            'ssh': 22,
            'telnet': 23,
            'smtp': 25,
            'dns': 53,
            'domain': 53,
            'dhcp': 67,
            'tftp': 69,
            'ftp': 21,
            'pop3': 110,
            'imap': 143,
            'snmp': 161,
            'ldap': 389,
            'https-alt': 8443,
            'mysql': 3306,
            'rdp': 3389,
            'kerberos': 88,
            'kpasswd': 464,
            'ldaps': 636,
            'msrpc': 135,
            'netbios-ssn': 139,
            'netbios-dgm': 138,
            'netbios-ns': 137,
            'smb': 445,
            'microsoft-ds': 445,
            'citrix': 1494,
            'citrix-ica': 1494,
            'citrix-xenapp': 1494,
            'ntp': 123,
            'time': 37,
            'daytime': 13,
            'chargen': 19,
            'echo': 7,
            'discard': 9,
            'systat': 11,
            'finger': 79,
            'whois': 43,
            'gopher': 70,
            'rje': 77,
            'hostname': 101,
            'iso-tsap': 102,
            'acr-nema': 104,
            'csnet-ns': 105,
            'rtelnet': 107,
            'pop-2': 109,
            'pop-3': 110,
            'sunrpc': 111,
            'ident': 113,
            'auth': 113,
            'sftp': 115,
            'uucp-path': 117,
            'nntp': 119,
            'pwdgen': 129,
            'loc-srv': 135,
            'imap2': 143,
            'news': 144,
            'www': 80,
            'ftp-data': 20,
            'netbios-ss': 139,
            'nameserver': 42,
            'snmptrap': 162,
            'lpd': 515,
            'cmd': 514,
            'syslog': 514,
            'tacacs': 49
        }
        
        # Identity mapping for object groups
        self.object_group_to_identity = {}
        
    def _generate_id(self) -> str:
        """Generate a UUID for Cradlepoint."""
        return str(uuid.uuid4())
    
    def _cidr_from_mask(self, mask: str) -> str:
        """Convert subnet mask to CIDR notation."""
        try:
            # Handle different mask formats
            if mask.startswith('255.'):
                # Convert dotted decimal to CIDR
                octets = mask.split('.')
                cidr = sum(bin(int(octet)).count('1') for octet in octets)
                return f"/{cidr}"
            elif mask.startswith('/'):
                return mask
            else:
                # Assume it's already a CIDR
                return f"/{mask}"
        except:
            return "/32"  # Default to single host
    
    def parse_config(self):
        """Parse the Cisco configuration file."""
        try:
            with open(self.config_file, 'r') as f:
                self.config_lines = f.readlines()
            
            # Parse all sections
            self.parse_zones()
            self.parse_interfaces()
            self.parse_object_groups()
            self.parse_acls()
            self.parse_class_maps()
            self.parse_policy_maps()
            self.parse_zone_pairs()
            
            # Create Cradlepoint components
            self.create_identities()
            self.create_filter_policies()
            self.create_zone_forwardings()
            
            # Add internet zone if requested
            if self.add_internet_zone:
                self.create_internet_zone()
            
        except Exception as e:
            print(f"Error parsing configuration: {e}")
            raise
    
    def parse_zones(self):
        """Parse security zones from configuration."""
        for line in self.config_lines:
            line = line.strip()
            if line.startswith('zone security '):
                zone_name = line.split('zone security ')[1]
                zone_id = self._generate_id()
                self.zones[zone_id] = {
                    '_id_': zone_id,
                    'name': zone_name
                }
    
    def parse_interfaces(self):
        """Parse interface configurations and zone assignments."""
        current_interface = None
        
        for line in self.config_lines:
            line = line.strip()
            
            # Interface definition
            if line.startswith('interface '):
                interface_name = line.split('interface ')[1]
                current_interface = {
                    'name': interface_name,
                    'zone': None,
                    'ip_address': None,
                    'subnet_mask': None
                }
                self.interfaces[interface_name] = current_interface
            
            # Zone assignment
            elif current_interface and line.startswith('zone-member security '):
                zone_name = line.split('zone-member security ')[1]
                current_interface['zone'] = zone_name
                
                # Add interface to zone
                # Find zone by name to get its ID
                zone_id = None
                for zid, zone in self.zones.items():
                    if zone['name'] == zone_name:
                        zone_id = zid
                        break
                
                if zone_id:
                    device_id = self._generate_id()
                    # Initialize devices dict if it doesn't exist
                    if 'devices' not in self.zones[zone_id]:
                        self.zones[zone_id]['devices'] = {}
                    self.zones[zone_id]['devices'][device_id] = {
                        '_id_': device_id,
                        'name': current_interface['name'],
                        'type': 'interface'
                    }
            
            # IP address assignment
            elif current_interface and line.startswith('ip address '):
                parts = line.split()
                if len(parts) >= 3:
                    current_interface['ip_address'] = parts[2]
                    if len(parts) >= 4:
                        current_interface['subnet_mask'] = parts[3]
            
            # Reset current interface when we hit a new section
            elif line and not line.startswith(' ') and not line.startswith('!') and not line.startswith('interface'):
                current_interface = None
    
    def parse_object_groups(self):
        """Parse object groups from configuration."""
        current_object_group = None
        
        for line in self.config_lines:
            line = line.strip()
            
            # Start of object group
            if line.startswith('object-group '):
                parts = line.split()
                if len(parts) >= 3:
                    group_type = parts[1]  # network, service, protocol, etc.
                    group_name = parts[2]
                    
                    current_object_group = {
                        'name': group_name,
                        'type': group_type,
                        'objects': []
                    }
                    self.object_groups[group_name] = current_object_group
            
            # End of object group - reset when we hit a new major section
            elif current_object_group and (line.startswith('!') or line.startswith('interface ') or line.startswith('ip ') or line.startswith('router ') or line.startswith('zone ') or line.startswith('class-map ') or line.startswith('policy-map ') or line.startswith('crypto ') or line.startswith('line ') or line.startswith('access-list ') or line.startswith('logging ') or line.startswith('ntp ') or line.startswith('snmp-server ') or line.startswith('tacacs ') or line.startswith('banner ') or line.startswith('mgcp ') or line.startswith('gatekeeper ') or line.startswith('control-plane ') or line.startswith('scheduler ') or line.startswith('end')):
                current_object_group = None
            
            # Object group entries (only if we're in an object group)
            elif current_object_group and (line.startswith('host ') or line.startswith('network ') or line.startswith('range ') or line.startswith('description ') or line.startswith('tcp ') or line.startswith('udp ') or line.startswith('tcp-udp ') or (line and not line.startswith('!') and not line.startswith('object-group') and not line.startswith('interface ') and not line.startswith('ip ') and not line.startswith('router ') and not line.startswith('zone ') and not line.startswith('class-map ') and not line.startswith('policy-map ') and not line.startswith('crypto ') and not line.startswith('line ') and not line.startswith('access-list ') and not line.startswith('logging ') and not line.startswith('ntp ') and not line.startswith('snmp-server ') and not line.startswith('tacacs ') and not line.startswith('banner ') and not line.startswith('mgcp ') and not line.startswith('gatekeeper ') and not line.startswith('control-plane ') and not line.startswith('scheduler ') and not line.startswith('end'))):
                # Parse different types of object group entries
                if current_object_group['type'] == 'network':
                    # Network object group entries
                    if 'host ' in line:
                        host_ip = line.split('host ')[1].strip()
                        current_object_group['objects'].append({
                            'type': 'host',
                            'value': host_ip
                        })
                    elif 'network ' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            network = parts[1]
                            mask = parts[2]
                            current_object_group['objects'].append({
                                'type': 'network',
                                'network': network,
                                'mask': mask
                            })
                    elif 'range ' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            start_ip = parts[1]
                            end_ip = parts[2]
                            current_object_group['objects'].append({
                                'type': 'range',
                                'start': start_ip,
                                'end': end_ip
                            })
                    elif not line.startswith('description '):
                        # Handle direct IP addresses (no host/network/range prefix)
                        parts = line.split()
                        if len(parts) >= 2:
                            network = parts[0]
                            mask = parts[1]
                            current_object_group['objects'].append({
                                'type': 'network',
                                'network': network,
                                'mask': mask
                            })
                        elif len(parts) == 1:
                            # Single IP address (treat as host)
                            current_object_group['objects'].append({
                                'type': 'host',
                                'value': parts[0]
                            })
                
                elif current_object_group['type'] == 'service':
                    # Service object group entries - collect all ports regardless of protocol
                    if line.startswith('tcp ') or line.startswith('udp ') or line.startswith('tcp-udp '):
                        parts = line.split()
                        if len(parts) >= 3 and parts[1] == 'eq':
                            port = parts[2]
                            if port.isdigit():
                                current_object_group['objects'].append({
                                    'type': 'port',
                                    'port': int(port)
                                })
                            elif port in self.port_map:
                                current_object_group['objects'].append({
                                    'type': 'port',
                                    'port': self.port_map[port]
                                })
                            else:
                                # Try to parse as integer, if that fails, keep as string for later resolution
                                try:
                                    port_num = int(port)
                                    current_object_group['objects'].append({
                                        'type': 'port',
                                        'port': port_num
                                    })
                                except ValueError:
                                    # Keep as string - will be resolved later or skipped if unknown
                                    current_object_group['objects'].append({
                                        'type': 'port',
                                        'port': port
                                    })
                    elif 'range ' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            start_port = int(parts[2])
                            end_port = int(parts[3])
                            current_object_group['objects'].append({
                                'type': 'range',
                                'start_port': start_port,
                                'end_port': end_port
                            })
                    elif 'object-group ' in line:
                        # Reference to another object group
                        ref_group = line.split('object-group ')[1].strip()
                        current_object_group['objects'].append({
                            'type': 'object_group',
                            'reference': ref_group
                        })
            
            # Reset current object group when we hit a new section
            elif line and not line.startswith(' ') and not line.startswith('!') and not line.startswith('object-group'):
                current_object_group = None
    
    def parse_acls(self):
        """Parse access control lists from configuration."""
        current_acl = None
        
        for line in self.config_lines:
            line = line.strip()
            
            # Start of ACL
            if line.startswith('ip access-list extended '):
                acl_name = line.split('ip access-list extended ')[1]
                current_acl = {
                    'name': acl_name,
                    'rules': []
                }
                self.acls[acl_name] = current_acl
            
            # ACL rules
            elif current_acl and (line.startswith(' ') or line.startswith('permit ') or line.startswith('deny ')):
                # Parse ACL rule
                rule = self._parse_acl_rule(line)
                if rule:
                    current_acl['rules'].append(rule)
            
            # Reset current ACL when we hit a new section
            elif line and not line.startswith(' ') and not line.startswith('!') and not line.startswith('ip access-list'):
                current_acl = None
    
    def _parse_acl_rule(self, line: str) -> Optional[Dict]:
        """Parse a single ACL rule."""
        original_line = line.strip()
        
        # Skip comments and empty lines
        if not original_line or original_line.startswith('!'):
            return None
        
        # Parse permit/deny rules
        if original_line.startswith('permit ') or original_line.startswith('deny '):
            parts = original_line.split()
            action = parts[0]
            
            # Check if parts[1] is a valid protocol
            valid_protocols = ['tcp', 'udp', 'icmp', 'ip']
            if len(parts) > 1 and parts[1].lower() in valid_protocols:
                protocol = parts[1]
                # Standard format: permit protocol source destination
                remaining_parts = parts[2:]
            else:
                # No explicit protocol, default to 'ip'
                protocol = 'ip'
                # All parts after 'permit'/'deny' are source/destination
                remaining_parts = parts[1:]
            
            # Map protocol to numeric value
            protocol_map = {
                'tcp': 6,
                'udp': 17,
                'icmp': 1,
                'ip': 0  # Any protocol
            }
            protocol_id = protocol_map.get(protocol.lower(), 6)  # Default to TCP
            
            rule = {
                'action': 'allow' if action == 'permit' else 'deny',
                'protocol': protocol,
                'protocol_id': protocol_id
            }
            
            # Parse the remaining parts based on patterns
            if len(remaining_parts) >= 6 and remaining_parts[0] == 'object-group' and remaining_parts[2] == 'object-group' and remaining_parts[4] == 'object-group':
                # Pattern: permit object-group SVC-ORION object-group NET-ORION object-group NET-LOCAL-NETS
                # This means: permit <service_group> <source_network_group> <destination_network_group>
                service_group = remaining_parts[1]
                source_network = remaining_parts[3] 
                destination_network = remaining_parts[5]
                
                # Service group goes to destination port
                rule['service_object_group'] = service_group
                # Source network group goes to source IP
                rule['source_object_group'] = source_network
                # Destination network group goes to destination IP
                rule['destination_object_group'] = destination_network
                
            elif len(remaining_parts) >= 4 and remaining_parts[0] == 'object-group' and remaining_parts[2] == 'object-group':
                # Check if first object-group is a service group (SVC- or SVCG- prefix)
                first_group = remaining_parts[1]
                is_service_group = first_group.startswith('SVC-') or first_group.startswith('SVCG-')
                
                if is_service_group and len(remaining_parts) >= 4:
                    # Pattern: permit object-group SVC-WEBTRAFFIC object-group NET-LOCAL-NETS any
                    # This means: permit <service_group> <source_network_group> any
                    service_group = remaining_parts[1]
                    source_network = remaining_parts[3]
                    destination = remaining_parts[4] if len(remaining_parts) > 4 else 'any'
                    
                    # Service group goes to destination port
                    rule['service_object_group'] = service_group
                    # Source network group goes to source IP
                    rule['source_object_group'] = source_network
                    # Destination
                    if destination == 'any':
                        rule['destination_ip'] = 'any'
                    elif destination.startswith('object-group '):
                        group_name = destination.split('object-group ')[1]
                        rule['destination_object_group'] = group_name
                    else:
                        rule['destination_object_group'] = destination
                else:
                    # Pattern: permit object-group NET-SQL-CMS object-group NET-LOCAL-NETS eq 445
                    # This means: permit <source_network_group> <destination_network_group> [port_spec]
                    source_network = remaining_parts[1]
                    destination_network = remaining_parts[3]
                    
                    # Source network group goes to source IP
                    rule['source_object_group'] = source_network
                    # Destination network group goes to destination IP
                    rule['destination_object_group'] = destination_network
                    
                    # Handle port specifications
                    if len(remaining_parts) >= 6 and remaining_parts[4] in ['eq', 'range', 'lt', 'gt']:
                        if remaining_parts[4] == 'eq':
                            rule['destination_port'] = remaining_parts[5]
                        elif remaining_parts[4] == 'range' and len(remaining_parts) >= 7:
                            rule['destination_port'] = f"{remaining_parts[5]}-{remaining_parts[6]}"
                        
            elif len(remaining_parts) >= 5 and remaining_parts[0] == 'object-group' and remaining_parts[2] == 'host':
                # Pattern: permit tcp object-group NET-LOCAL-NETS host 138.229.6.104 eq 7002
                # This means: permit <protocol> <source_network_group> host <destination_ip> [port_spec]
                source_network = remaining_parts[1]
                destination_ip = remaining_parts[3]
                
                # Source network group goes to source IP
                rule['source_object_group'] = source_network
                # Destination IP goes to destination IP
                rule['destination_ip'] = destination_ip
                
                # Handle port specifications
                if len(remaining_parts) >= 6 and remaining_parts[4] in ['eq', 'range', 'lt', 'gt']:
                    if remaining_parts[4] == 'eq':
                        rule['destination_port'] = remaining_parts[5]
                    elif remaining_parts[4] == 'range' and len(remaining_parts) >= 7:
                        rule['destination_port'] = f"{remaining_parts[5]}-{remaining_parts[6]}"
                        
            elif len(remaining_parts) >= 5 and remaining_parts[0] == 'object-group' and remaining_parts[2] == 'object-group' and remaining_parts[4] == 'eq':
                # Pattern: permit tcp object-group NET-LOCAL-NETS object-group PORTAL-OUTLOYALTY.BEALLSINC.COM eq 5000
                # This means: permit <protocol> <source_network_group> object-group <destination_group> eq <port>
                source_network = remaining_parts[1]
                destination_group = remaining_parts[3]
                port = remaining_parts[5]
                
                # Source network group goes to source IP
                rule['source_object_group'] = source_network
                # Destination group goes to destination IP
                rule['destination_object_group'] = destination_group
                # Port specification
                rule['destination_port'] = port
                
            elif len(remaining_parts) == 2:
                # Pattern: permit source destination
                source = remaining_parts[0]
                destination = remaining_parts[1]
                
                # Parse source
                if source == 'any':
                    rule['source_ip'] = 'any'
                elif source.startswith('host '):
                    rule['source_ip'] = source.split('host ')[1]
                elif source.startswith('object-group '):
                    group_name = source.split('object-group ')[1]
                    rule['source_object_group'] = group_name
                else:
                    rule['source_object_group'] = source
                
                # Parse destination
                if destination == 'any':
                    rule['destination_ip'] = 'any'
                elif destination.startswith('host '):
                    rule['destination_ip'] = destination.split('host ')[1]
                elif destination.startswith('object-group '):
                    group_name = destination.split('object-group ')[1]
                    rule['destination_object_group'] = group_name
                else:
                    rule['destination_object_group'] = destination
                    
            elif len(remaining_parts) == 1:
                # Pattern: permit source (destination is 'any')
                source = remaining_parts[0]
                rule['destination_ip'] = 'any'
                
                # Parse source
                if source == 'any':
                    rule['source_ip'] = 'any'
                elif source.startswith('host '):
                    rule['source_ip'] = source.split('host ')[1]
                elif source.startswith('object-group '):
                    group_name = source.split('object-group ')[1]
                    rule['source_object_group'] = group_name
                else:
                    rule['source_object_group'] = source
            
            return rule
        
        return None
    
    def parse_class_maps(self):
        """Parse class maps from configuration."""
        current_class_map = None
        
        for line in self.config_lines:
            line = line.strip()
            
            # Start of class map
            if line.startswith('class-map type inspect match-any '):
                class_map_name = line.split('class-map type inspect match-any ')[1]
                current_class_map = {
                    'name': class_map_name,
                    'match_type': 'match-any',
                    'acl_references': [],
                    'object_group_references': []
                }
                self.class_maps[class_map_name] = current_class_map
            
            # Class map match statement
            elif current_class_map and line.startswith('match access-group name '):
                acl_name = line.split()[3]
                current_class_map['acl_references'].append(acl_name)
            
            # Class map match object-group statement
            elif current_class_map and line.startswith('match object-group '):
                object_group_name = line.split()[2]
                current_class_map['object_group_references'].append(object_group_name)
            
            # Reset current_class_map when we hit a new section
            elif line and not line.startswith(' ') and not line.startswith('!') and not line.startswith('class-map') and not line.startswith('policy-map'):
                current_class_map = None
    
    def parse_policy_maps(self):
        """Parse policy maps from configuration."""
        current_policy_map = None
        
        for line in self.config_lines:
            line = line.strip()
            
            # Start of policy map
            if line.startswith('policy-map type inspect '):
                policy_map_name = line.split('policy-map type inspect ')[1]
                current_policy_map = {
                    'name': policy_map_name,
                    'class_actions': []
                }
                self.policy_maps[policy_map_name] = current_policy_map
            
            # Policy map class action
            elif current_policy_map and line.startswith('class type inspect '):
                class_name = line.split('class type inspect ')[1]
                current_policy_map['class_actions'].append({
                    'class_name': class_name,
                    'actions': []
                })
            
            # Policy map actions
            elif current_policy_map and line.startswith('  '):
                # Parse various policy map actions
                if 'inspect ' in line:
                    protocol = line.split('inspect ')[1].strip()
                    current_policy_map['class_actions'][-1]['actions'].append({
                        'type': 'inspect',
                        'protocol': protocol
                    })
                elif 'drop' in line:
                    current_policy_map['class_actions'][-1]['actions'].append({
                        'type': 'drop'
                    })
                elif 'pass' in line:
                    current_policy_map['class_actions'][-1]['actions'].append({
                        'type': 'pass'
                    })
            
            # Reset current_policy_map when we hit a new section
            elif line and not line.startswith(' ') and not line.startswith('!') and not line.startswith('class-map') and not line.startswith('policy-map'):
                current_policy_map = None
    
    def parse_zone_pairs(self):
        """Parse zone pairs from configuration."""
        for line in self.config_lines:
            line = line.strip()
            if line.startswith('zone-pair security '):
                parts = line.split()
                if len(parts) >= 6:  # zone-pair security <name> source <source-zone> destination <destination-zone>
                    pair_name = parts[2]
                    # Look for 'source' and 'destination' keywords
                    source_zone = None
                    destination_zone = None
                    
                    for i, part in enumerate(parts):
                        if part == 'source' and i + 1 < len(parts):
                            source_zone = parts[i + 1]
                        elif part == 'destination' and i + 1 < len(parts):
                            destination_zone = parts[i + 1]
                    
                    if source_zone and destination_zone:
                        self.zone_pairs[pair_name] = {
                            'name': pair_name,
                            'source_zone': source_zone,
                            'destination_zone': destination_zone,
                            'policy_map': None
                        }
            
            # Policy map assignment to zone pair
            elif line.startswith('service-policy type inspect '):
                parts = line.split()
                if len(parts) >= 4:
                    policy_map_name = parts[3]
                    # Find the most recent zone pair to assign this policy
                    if self.zone_pairs:
                        last_pair = list(self.zone_pairs.values())[-1]
                        last_pair['policy_map'] = policy_map_name
    
    def create_identities(self):
        """Create IP and port identities from object groups."""
        # Create IP identities from network object groups
        for group_name, group in self.object_groups.items():
            if group['type'] == 'network' and group['objects']:
                identity_id = self._generate_id()
                members = {}
                
                for i, obj in enumerate(group['objects']):
                    if obj['type'] == 'host':
                        # Only add if it's a valid IP address
                        if self._is_valid_ip_address(obj['value']):
                            members[str(i)] = {'address': obj['value']}
                    elif obj['type'] == 'network':
                        # Only add if it's a valid IP address
                        if self._is_valid_ip_address(obj['network']):
                            cidr = self._cidr_from_mask(obj['mask'])
                            members[str(i)] = {'address': f"{obj['network']}{cidr}"}
                    elif obj['type'] == 'range':
                        # Only add if both start and end are valid IP addresses
                        if self._is_valid_ip_address(obj['start']) and self._is_valid_ip_address(obj['end']):
                            members[str(i)] = {'address': obj['start']}
                            if i+1 < len(group['objects']):
                                members[str(i+1)] = {'address': obj['end']}
                
                if members:
                    identity_obj = {
                        '_id_': identity_id,
                        'name': group_name,
                        'friendly_name': '',
                        'members': list(members.values())
                    }
                    self.identities['ip'].append(identity_obj)
                    # Map object group to identity ID
                    self.object_group_to_identity[group_name] = identity_id
        
        # Create port identities from service object groups
        for group_name, group in self.object_groups.items():
            if group['type'] == 'service' and group['objects']:
                # Check if this service group has both TCP and UDP ports
                protocols = self._get_protocol_identities_for_service_group(group_name)
                has_multiple_protocols = len(protocols) > 1
                
                if has_multiple_protocols:
                    # Create separate identities for each protocol/port combination
                    # Parse the config to determine which ports are TCP and which are UDP
                    tcp_ports = set()
                    udp_ports = set()
                    
                    # Parse the original config to find TCP and UDP entries
                    in_service_group = False
                    for line in self.config_lines:
                        line_stripped = line.strip()
                        
                        if line_stripped.startswith(f'object-group service {group_name}') or line_stripped.startswith(f'object-group service {group_name} '):
                            in_service_group = True
                            continue
                        elif in_service_group:
                            if line_stripped.startswith('!'):
                                break
                            elif line_stripped.startswith('object-group '):
                                break
                            elif (line_stripped.startswith('class-map ') or line_stripped.startswith('policy-map ') or 
                                  line_stripped.startswith('zone-pair ') or line_stripped.startswith('ip access-list ') or
                                  line_stripped.startswith('interface ') or line_stripped.startswith('router ') or
                                  line_stripped.startswith('zone security ')):
                                break
                            elif not line_stripped or line_stripped.startswith('description '):
                                continue
                            elif line_stripped.startswith('tcp '):
                                parts = line_stripped.split()
                                if len(parts) >= 3 and parts[1] == 'eq':
                                    try:
                                        port = int(parts[2])
                                        tcp_ports.add(port)
                                    except ValueError:
                                        port_name = parts[2]
                                        if port_name in self.port_map:
                                            tcp_ports.add(self.port_map[port_name])
                            elif line_stripped.startswith('udp '):
                                parts = line_stripped.split()
                                if len(parts) >= 3 and parts[1] == 'eq':
                                    try:
                                        port = int(parts[2])
                                        udp_ports.add(port)
                                    except ValueError:
                                        port_name = parts[2]
                                        if port_name in self.port_map:
                                            udp_ports.add(self.port_map[port_name])
                            elif line_stripped.startswith('tcp-udp '):
                                parts = line_stripped.split()
                                if len(parts) >= 3 and parts[1] == 'eq':
                                    try:
                                        port = int(parts[2])
                                        tcp_ports.add(port)
                                        udp_ports.add(port)
                                    except ValueError:
                                        port_name = parts[2]
                                        if port_name in self.port_map:
                                            tcp_ports.add(self.port_map[port_name])
                                            udp_ports.add(self.port_map[port_name])
                    
                    # Create one identity per protocol with all ports for that protocol combined
                    if tcp_ports:
                        tcp_identity_id = self._generate_id()
                        tcp_members = [{'start': port, 'end': port} for port in sorted(tcp_ports)]
                        tcp_identity_obj = {
                            '_id_': tcp_identity_id,
                            'name': f"{group_name}-TCP",
                            'members': tcp_members
                        }
                        self.identities['port'].append(tcp_identity_obj)
                        self.object_group_to_identity[f"{group_name}-TCP"] = tcp_identity_id
                        # Also map lowercase for backward compatibility
                        self.object_group_to_identity[f"{group_name}-tcp"] = tcp_identity_id
                    
                    if udp_ports:
                        udp_identity_id = self._generate_id()
                        udp_members = [{'start': port, 'end': port} for port in sorted(udp_ports)]
                        udp_identity_obj = {
                            '_id_': udp_identity_id,
                            'name': f"{group_name}-UDP",
                            'members': udp_members
                        }
                        self.identities['port'].append(udp_identity_obj)
                        self.object_group_to_identity[f"{group_name}-UDP"] = udp_identity_id
                        # Also map lowercase for backward compatibility
                        self.object_group_to_identity[f"{group_name}-udp"] = udp_identity_id
                    
                    # Also create a combined mapping for backward compatibility
                    # Use the first identity (TCP if available, otherwise UDP)
                    if tcp_ports:
                        self.object_group_to_identity[group_name] = tcp_identity_id
                    elif udp_ports:
                        self.object_group_to_identity[group_name] = udp_identity_id
                else:
                    # Single protocol - create a single identity as before
                    identity_id = self._generate_id()
                    members = {}
                    
                    for i, obj in enumerate(group['objects']):
                        if obj['type'] == 'port' and 'port' in obj:
                            # Handle both numeric ports and port names
                            if isinstance(obj['port'], int):
                                members[str(i)] = {
                                    'start': obj['port'],
                                    'end': obj['port']
                                }
                            else:
                                # Try to resolve port name to number
                                port_name = obj['port']
                                if port_name in self.port_map:
                                    members[str(i)] = {
                                        'start': self.port_map[port_name],
                                        'end': self.port_map[port_name]
                                    }
                                else:
                                    # Try to parse as integer, if that fails, skip this port
                                    try:
                                        port_num = int(port_name)
                                        members[str(i)] = {
                                            'start': port_num,
                                            'end': port_num
                                        }
                                    except ValueError:
                                        # Skip unknown port names - they can't be used in Cradlepoint
                                        print(f"Warning: Unknown port name '{port_name}' in service object group, skipping")
                                        continue
                        elif obj['type'] == 'range' and 'start_port' in obj:
                            members[str(i)] = {
                                'start': obj['start_port'],
                                'end': obj['end_port']
                            }
                        elif obj['type'] == 'object_group' and 'reference' in obj:
                            # Handle nested object group references
                            ref_group = obj['reference']
                            if ref_group in self.object_group_to_identity:
                                # This is a reference to another object group
                                # For now, we'll create a placeholder
                                members[str(i)] = {
                                    'start': 0,  # Placeholder
                                    'end': 0
                                }
                    
                    if members:
                        identity_obj = {
                            '_id_': identity_id,
                            'name': group_name,
                            'members': list(members.values())
                        }
                        self.identities['port'].append(identity_obj)
                        # Map object group to identity ID
                        self.object_group_to_identity[group_name] = identity_id
    
    def _is_acl_applied_somewhere(self, acl_name: str) -> bool:
        """Check if an ACL is actually applied somewhere in the configuration."""
        # Check if ACL is applied to interfaces
        for line in self.config_lines:
            line = line.strip()
            if f'ip access-group {acl_name}' in line or f'access-group {acl_name}' in line:
                return True
        
        # Check if ACL is applied to zone pairs or other contexts
        for line in self.config_lines:
            line = line.strip()
            if acl_name in line and ('service-policy' in line or 'zone-pair' in line):
                return True
        
        # For now, assume ACLs are only used in class maps if not found elsewhere
        # This means orphaned ACLs won't get filter policies
        return False
    
    def create_filter_policies(self):
        """Create filter policies from ACLs and policy maps."""
        # First, identify which ACLs are used in class maps
        acls_used_in_class_maps = set()
        for class_map in self.class_maps.values():
            for acl_ref in class_map.get('acl_references', []):
                acls_used_in_class_maps.add(acl_ref)
        
        # Only create filter policies for ACLs that are NOT used in class maps
        # AND are actually applied somewhere (not orphaned)
        for acl_name, acl in self.acls.items():
            if acl_name not in acls_used_in_class_maps and self._is_acl_applied_somewhere(acl_name):
                policy_id = self._generate_id()
                rules = {}
                
                rule_index = 0
                for acl_rule in acl.get('rules', []):
                    cradlepoint_rules = self._convert_acl_rule_to_cradlepoint(acl_rule, rule_index, None, acl_name)
                    for cradlepoint_rule in cradlepoint_rules:
                        if cradlepoint_rule:
                            rules[str(rule_index)] = cradlepoint_rule
                            rule_index += 1
                
                if rules:  # Only create policy if there are rules
                    # Consolidate rules to reduce redundancy
                    consolidated_rules = self._consolidate_rules(rules)
                    self.filter_policies[policy_id] = {
                        '_id_': policy_id,
                        'name': acl_name,
                        'default_action': 'deny',
                        'rules': consolidated_rules
                    }
        
        # Create filter policies from policy maps
        for policy_name, policy in self.policy_maps.items():
            policy_id = self._generate_id()
            rules = {}
            
            # Find the destination zone for this policy map
            destination_zone = None
            for pair_name, pair in self.zone_pairs.items():
                if pair.get('policy_map') == policy_name:
                    destination_zone = pair.get('destination_zone')
                    break
            
            # If no destination zone found in zone pairs, extract from policy map name
            if not destination_zone:
                # Extract zone from policy map name (e.g., PM_ZBF_WAN_POS -> WAN)
                if 'WAN' in policy_name:
                    destination_zone = 'WAN'
                elif 'POS' in policy_name:
                    destination_zone = 'WAN'  # POS rules should go to WAN
                else:
                    destination_zone = 'WAN'  # Default to WAN
            
            rule_index = 0
            for class_action in policy.get('class_actions', []):
                class_name = class_action['class_name']
                
                # Find the class map
                if class_name in self.class_maps:
                    class_map = self.class_maps[class_name]
                    
                    # Collect rules from all ACLs referenced by this class map
                    for acl_ref in class_map.get('acl_references', []):
                        if acl_ref in self.acls:
                            acl = self.acls[acl_ref]
                            acl_rule_index = 0  # Reset rule index for each ACL
                            for acl_rule in acl.get('rules', []):
                                # Convert ACL rule to Cradlepoint rules (may return multiple rules for multiple protocols)
                                cradlepoint_rules = self._convert_acl_rule_to_cradlepoint(acl_rule, rule_index, destination_zone, acl_ref)
                                for cradlepoint_rule in cradlepoint_rules:
                                    if cradlepoint_rule:
                                        rules[str(rule_index)] = cradlepoint_rule
                                        rule_index += 1  # Global rule index for the filter policy
                                acl_rule_index += 1  # ACL-specific rule index (increment once per ACL rule)
                    
                    # Handle object group references
                    for obj_group_ref in class_map.get('object_group_references', []):
                        if obj_group_ref in self.object_group_to_identity:
                            # Create a rule that references the object group identity
                            identity_id = self.object_group_to_identity[obj_group_ref]
                            rule = {
                                'action': 'allow',
                                'ip_version': 'ip4',
                                'name': f"OBJ-{obj_group_ref}",
                                'priority': rule_index * 10,
                                'dst': {'port': [], 'ip': {'0': {'identity': identity_id}}},
                                'src': {'mac': [], 'port': [], 'ip': []},
                                'app_sets': [],
                                'protocols': {'0': {'identity': 6}}  # TCP
                            }
                            rules[str(rule_index)] = rule
                            rule_index += 1
                
                # Apply actions from policy map
                for action in class_action.get('actions', []):
                    if action['type'] == 'inspect':
                        # Allow traffic for inspection
                        pass
                    elif action['type'] == 'drop':
                        # Add deny rule
                        deny_rule = {
                            'action': 'deny',
                            'ip_version': 'ip4',
                            'name': f"DENY-{class_name}",
                            'priority': rule_index * 10,
                            'src': {'mac': []},
                            'app_sets': [],
                            'protocols': {'0': {'identity': 6}}
                        }
                        rules[str(rule_index)] = deny_rule
                        rule_index += 1
                    elif action['type'] == 'pass':
                        # Allow traffic
                        pass
            
            # Consolidate rules to reduce redundancy
            consolidated_rules = self._consolidate_rules(rules)
            self.filter_policies[policy_id] = {
                '_id_': policy_id,
                'name': policy_name,
                'default_action': 'deny',
                'rules': consolidated_rules
            }
        
        # Create default policies if no policy maps exist
        if not self.filter_policies:
            # Default Allow All policy
            allow_policy_id = self._generate_id()
            self.filter_policies[allow_policy_id] = {
                '_id_': allow_policy_id,
                'name': 'Default Allow All',
                'default_action': 'deny',
                'rules': {
                    '0': {
                        'action': 'allow',
                        'ip_version': 'ip4',
                        'name': 'Allow All',
                        'priority': 10,
                        'src': {'mac': []},
                        'app_sets': [],
                        'protocols': {'0': {'identity': 6}}
                    }
                }
            }
            
            # Default Deny All policy
            deny_policy_id = self._generate_id()
            self.filter_policies[deny_policy_id] = {
                '_id_': deny_policy_id,
                'name': 'Default Deny All',
                'default_action': 'deny',
                'rules': {
                    '0': {
                        'action': 'deny',
                        'ip_version': 'ip4',
                        'name': 'Deny All',
                        'priority': 20,
                        'src': {'mac': []},
                        'app_sets': [],
                        'protocols': {'0': {'identity': 6}}
                    }
                }
            }
    
    def _convert_acl_rule_to_cradlepoint(self, acl_rule: Dict, rule_index: int, destination_zone: str = None, acl_name: str = None) -> List[Dict]:
        """Convert an ACL rule to Cradlepoint format. Returns a list of rules (one per protocol if multiple protocols)."""
        if not acl_rule:
            return []
        
        # Build source and destination identities (these are common to all protocol rules)
        src_identities = []
        dst_identities = []
        src_port_identities = []
        
        # Handle source
        if 'source_object_group' in acl_rule:
            obj_group = acl_rule['source_object_group']
            if obj_group in self.object_group_to_identity:
                identity_id = self.object_group_to_identity[obj_group]
                # Network object group -> IP identity
                src_identities.append({'identity': identity_id})
        elif 'source_ip' in acl_rule and acl_rule['source_ip'] != 'any':
            # Create individual IP identity if needed
            ip = acl_rule['source_ip']
            identity_id = self._get_or_create_ip_identity(ip)
            if identity_id:  # Only add if we got a valid identity ID
                src_identities.append({'identity': identity_id})
        
        # Handle destination (IP, not port)
        if 'destination_object_group' in acl_rule:
            obj_group = acl_rule['destination_object_group']
            if obj_group in self.object_group_to_identity:
                identity_id = self.object_group_to_identity[obj_group]
                # Only add if it's NOT a service object group (service groups are for ports)
                if not (obj_group.startswith('SVC-') or obj_group.startswith('SVCG-')):
                    # Network object group -> IP identity
                    dst_identities.append({'identity': identity_id})
        elif 'destination_ip' in acl_rule and acl_rule['destination_ip'] != 'any':
            # Create individual IP identity if needed
            ip = acl_rule['destination_ip']
            identity_id = self._get_or_create_ip_identity(ip)
            if identity_id:  # Only add if we got a valid identity ID
                dst_identities.append({'identity': identity_id})
        
        # Handle source ports
        if 'source_port' in acl_rule:
            port = acl_rule['source_port']
            identity_id = self._get_or_create_port_identity(port)
            if identity_id:
                src_port_identities.append({'identity': identity_id})
        
        # Handle destination ports (non-service-group) - will be added to rules below
        non_service_dst_port_identities = []
        if 'destination_port' in acl_rule and 'service_object_group' not in acl_rule:
            port = acl_rule['destination_port']
            identity_id = self._get_or_create_port_identity(port)
            if identity_id:
                non_service_dst_port_identities.append({'identity': identity_id})
        
        # Create base rule name
        base_rule_name = self._create_rule_name(acl_rule, destination_zone, acl_name, -1)
        
        # Check if this rule uses a service object group with multiple protocols
        rules = []
        if 'service_object_group' in acl_rule:
            service_group = acl_rule['service_object_group']
            protocol_identities = self._get_protocol_identities_for_service_group(service_group)
            
            if len(protocol_identities) > 1:
                # Create separate rules for each protocol
                protocol_names = {6: 'TCP', 17: 'UDP', 1: 'ICMP'}
                for i, protocol_id in enumerate(protocol_identities):
                    protocol_name = protocol_names.get(protocol_id, f'PROTO-{protocol_id}')
                    rule_name = f"{base_rule_name}-{protocol_name}"
                    
                    # Get the port identity for this protocol
                    dst_port_identities = []
                    protocol_key = 'TCP' if protocol_id == 6 else 'UDP' if protocol_id == 17 else None
                    if protocol_key and f"{service_group}-{protocol_key}" in self.object_group_to_identity:
                        dst_port_identities.append({'identity': self.object_group_to_identity[f"{service_group}-{protocol_key}"]})
                    
                    # Combine service group ports with any non-service-group ports
                    all_dst_port_identities = dst_port_identities + non_service_dst_port_identities
                    
                    rule = {
                        'action': acl_rule.get('action', 'allow'),
                        'ip_version': 'ip4',
                        'name': rule_name,
                        'priority': (rule_index + i) * 10,
                        'app_sets': [],
                        'protocols': {'0': {'identity': protocol_id}},
                        'dst': {
                            'ip': {str(j): identity for j, identity in enumerate(dst_identities)} if dst_identities else [],
                            'port': {str(j): identity for j, identity in enumerate(all_dst_port_identities)} if all_dst_port_identities else []
                        },
                        'src': {
                            'ip': {str(j): identity for j, identity in enumerate(src_identities)} if src_identities else [],
                            'port': {str(j): identity for j, identity in enumerate(src_port_identities)} if src_port_identities else [],
                            'mac': []
                        }
                    }
                    rules.append(rule)
            else:
                # Single protocol - create one rule
                protocol_id = protocol_identities[0] if protocol_identities else 6
                dst_port_identities = []
                if service_group in self.object_group_to_identity:
                    dst_port_identities.append({'identity': self.object_group_to_identity[service_group]})
                
                # Combine service group ports with any non-service-group ports
                all_dst_port_identities = dst_port_identities + non_service_dst_port_identities
                
                rule = {
                    'action': acl_rule.get('action', 'allow'),
                    'ip_version': 'ip4',
                    'name': base_rule_name,
                    'priority': rule_index * 10,
                    'app_sets': [],
                    'protocols': {'0': {'identity': protocol_id}},
                    'dst': {
                        'ip': {str(j): identity for j, identity in enumerate(dst_identities)} if dst_identities else [],
                        'port': {str(j): identity for j, identity in enumerate(all_dst_port_identities)} if all_dst_port_identities else []
                    },
                    'src': {
                        'ip': {str(j): identity for j, identity in enumerate(src_identities)} if src_identities else [],
                        'port': {str(j): identity for j, identity in enumerate(src_port_identities)} if src_port_identities else [],
                        'mac': []
                    }
                }
                rules.append(rule)
        else:
            # No service object group - create single rule
            protocol = acl_rule.get('protocol', 'tcp').lower()
            protocol_id = self._get_protocol_identity_for_rule(acl_rule)
            
            # Use non-service-group destination ports
            dst_port_identities = non_service_dst_port_identities
            
            if protocol in ['ip', 'ipv4', 'ipv6', 'any']:
                protocols = []
            else:
                protocols = {'0': {'identity': protocol_id}}
            
            rule = {
                'action': acl_rule.get('action', 'allow'),
                'ip_version': 'ip4',
                'name': base_rule_name,
                'priority': rule_index * 10,
                'app_sets': [],
                'protocols': protocols,
                'dst': {
                    'ip': {str(j): identity for j, identity in enumerate(dst_identities)} if dst_identities else [],
                    'port': {str(j): identity for j, identity in enumerate(dst_port_identities)} if dst_port_identities else []
                },
                'src': {
                    'ip': {str(j): identity for j, identity in enumerate(src_identities)} if src_identities else [],
                    'port': {str(j): identity for j, identity in enumerate(src_port_identities)} if src_port_identities else [],
                    'mac': []
                }
            }
            rules.append(rule)
        
        return rules

    def _consolidate_rules(self, rules: Dict) -> Dict:
        """Consolidate rules that have the same protocol and port but different sources or destinations."""
        consolidated_rules = {}
        rule_groups = {}
        
        # Group rules by protocol, port, source IPs, and destination IPs combination
        for rule_id, rule in rules.items():
            # Create a key based on protocol, port, source IPs, and destination IPs
            protocol_key = self._get_rule_protocol_key(rule)
            port_key = self._get_rule_port_key(rule)
            src_ip_key = self._get_rule_ip_key(rule, 'src')
            dst_ip_key = self._get_rule_ip_key(rule, 'dst')
            action = rule.get('action', 'allow')
            
            # Create a composite key for grouping - include source and destination IPs
            # This ensures rules with different source/destination IPs are not consolidated
            group_key = f"{action}_{protocol_key}_{port_key}_{src_ip_key}_{dst_ip_key}"
            
            if group_key not in rule_groups:
                rule_groups[group_key] = {
                    'action': action,
                    'protocol_key': protocol_key,
                    'port_key': port_key,
                    'rules': []
                }
            
            rule_groups[group_key]['rules'].append(rule)
        
        # Consolidate rules within each group
        rule_index = 0
        for group_key, group in rule_groups.items():
            if len(group['rules']) == 1:
                # Single rule, no consolidation needed - keep original name
                rule = group['rules'][0].copy()
                consolidated_rules[str(rule_index)] = rule
                rule_index += 1
            else:
                # Multiple rules, consolidate them
                consolidated_rule = self._merge_rules(group['rules'])
                if consolidated_rule:
                    consolidated_rules[str(rule_index)] = consolidated_rule
                    rule_index += 1
        
        # Check for duplicate rule names and add numbering only when necessary
        consolidated_rules = self._handle_duplicate_rule_names(consolidated_rules)
        
        return consolidated_rules

    def _handle_duplicate_rule_names(self, rules: Dict) -> Dict:
        """Handle duplicate rule names by adding numbering only when necessary."""
        name_counts = {}
        updated_rules = {}
        
        # Count occurrences of each rule name
        for rule_id, rule in rules.items():
            rule_name = rule['name']
            if rule_name not in name_counts:
                name_counts[rule_name] = []
            name_counts[rule_name].append(rule_id)
        
        # Process rules and add numbering only for duplicates
        rule_index = 0
        for rule_id, rule in rules.items():
            rule_name = rule['name']
            
            # If this rule name appears multiple times, add numbering
            if len(name_counts[rule_name]) > 1:
                # Find the index of this rule among rules with the same name
                same_name_rules = name_counts[rule_name]
                rule_position = same_name_rules.index(rule_id) + 1
                updated_rule = rule.copy()
                updated_rule['name'] = f"{rule_name}-{rule_position}"
                updated_rules[str(rule_index)] = updated_rule
            else:
                # Single occurrence, keep original name
                updated_rules[str(rule_index)] = rule
            
            rule_index += 1
        
        return updated_rules

    def _update_rule_name_with_index(self, rule_name: str, new_index: int) -> str:
        """Update a rule name to use the new index, removing any existing index."""
        # Remove any existing index pattern (e.g., "-1", "-2", etc.)
        import re
        # Pattern to match - followed by digits at the end
        pattern = r'-\d+$'
        base_name = re.sub(pattern, '', rule_name)
        return f"{base_name}-{new_index}"

    def _get_rule_protocol_key(self, rule: Dict) -> str:
        """Get a key representing the protocol configuration of a rule."""
        protocols = rule.get('protocols', {})
        if isinstance(protocols, list):
            return "any"
        elif isinstance(protocols, dict):
            protocol_ids = []
            for key, protocol in protocols.items():
                if 'identity' in protocol:
                    protocol_ids.append(str(protocol['identity']))
            return "_".join(sorted(protocol_ids))
        return "unknown"

    def _get_rule_port_key(self, rule: Dict) -> str:
        """Get a key representing the port configuration of a rule."""
        dst_ports = rule.get('dst', {}).get('port', [])
        src_ports = rule.get('src', {}).get('port', [])
        
        if isinstance(dst_ports, dict):
            dst_port_ids = [str(port.get('identity', '')) for port in dst_ports.values()]
        else:
            dst_port_ids = []
            
        if isinstance(src_ports, dict):
            src_port_ids = [str(port.get('identity', '')) for port in src_ports.values()]
        else:
            src_port_ids = []
        
        return f"dst_{'_'.join(sorted(dst_port_ids))}_src_{'_'.join(sorted(src_port_ids))}"
    
    def _get_rule_ip_key(self, rule: Dict, direction: str) -> str:
        """Get a key representing the IP configuration of a rule for a given direction (src or dst)."""
        ips = rule.get(direction, {}).get('ip', [])
        
        if isinstance(ips, dict):
            ip_ids = [str(ip.get('identity', '')) for ip in ips.values()]
        elif isinstance(ips, list):
            ip_ids = [str(ip.get('identity', '')) for ip in ips if isinstance(ip, dict)]
        else:
            ip_ids = []
        
        # Sort to ensure consistent grouping
        return '_'.join(sorted(ip_ids)) if ip_ids else 'any'

    def _merge_rules(self, rules: List[Dict]) -> Optional[Dict]:
        """Merge multiple rules with the same protocol and port into a single rule."""
        if not rules:
            return None
        
        # Use the first rule as the base
        base_rule = rules[0].copy()
        
        # Collect all source and destination identities
        all_src_ips = []
        all_dst_ips = []
        all_src_ports = []
        all_dst_ports = []
        
        for rule in rules:
            # Collect source IPs
            src_ips = rule.get('src', {}).get('ip', [])
            if isinstance(src_ips, dict):
                all_src_ips.extend(src_ips.values())
            elif isinstance(src_ips, list):
                all_src_ips.extend(src_ips)
            
            # Collect destination IPs
            dst_ips = rule.get('dst', {}).get('ip', [])
            if isinstance(dst_ips, dict):
                all_dst_ips.extend(dst_ips.values())
            elif isinstance(dst_ips, list):
                all_dst_ips.extend(dst_ips)
            
            # Collect source ports
            src_ports = rule.get('src', {}).get('port', [])
            if isinstance(src_ports, dict):
                all_src_ports.extend(src_ports.values())
            elif isinstance(src_ports, list):
                all_src_ports.extend(src_ports)
            
            # Collect destination ports
            dst_ports = rule.get('dst', {}).get('port', [])
            if isinstance(dst_ports, dict):
                all_dst_ports.extend(dst_ports.values())
            elif isinstance(dst_ports, list):
                all_dst_ports.extend(dst_ports)
        
        # Remove duplicates while preserving order
        unique_src_ips = []
        seen_src_ips = set()
        for ip in all_src_ips:
            ip_key = str(ip.get('identity', ''))
            if ip_key not in seen_src_ips:
                unique_src_ips.append(ip)
                seen_src_ips.add(ip_key)
        
        unique_dst_ips = []
        seen_dst_ips = set()
        for ip in all_dst_ips:
            ip_key = str(ip.get('identity', ''))
            if ip_key not in seen_dst_ips:
                unique_dst_ips.append(ip)
                seen_dst_ips.add(ip_key)
        
        unique_src_ports = []
        seen_src_ports = set()
        for port in all_src_ports:
            port_key = str(port.get('identity', ''))
            if port_key not in seen_src_ports:
                unique_src_ports.append(port)
                seen_src_ports.add(port_key)
        
        unique_dst_ports = []
        seen_dst_ports = set()
        for port in all_dst_ports:
            port_key = str(port.get('identity', ''))
            if port_key not in seen_dst_ports:
                unique_dst_ports.append(port)
                seen_dst_ports.add(port_key)
        
        # Update the base rule with consolidated identities
        base_rule['src']['ip'] = {str(i): identity for i, identity in enumerate(unique_src_ips)} if unique_src_ips else []
        base_rule['dst']['ip'] = {str(i): identity for i, identity in enumerate(unique_dst_ips)} if unique_dst_ips else []
        base_rule['src']['port'] = {str(i): identity for i, identity in enumerate(unique_src_ports)} if unique_src_ports else []
        base_rule['dst']['port'] = {str(i): identity for i, identity in enumerate(unique_dst_ports)} if unique_dst_ports else []
        
        # Keep the original rule name without consolidation suffix
        
        return base_rule

    def _create_directional_policy_name(self, acl_name: str, rules: List[Dict]) -> str:
        """Create a directional policy name based on the source and destination patterns in the rules."""
        def normalize_name(name: str) -> str:
            # Keep prefixes but clean up object group prefixes for readability
            name = name.replace('NET-', '').replace('HOSTG-', '').replace('HOST-', '').replace('NETG-', '')
            return name.upper()
        
        if not rules:
            # Fallback to original ACL name
            return acl_name
        
        # Handle both list and dictionary formats
        if isinstance(rules, list):
            first_rule = rules[0]
        else:
            # Dictionary format
            first_rule_key = list(rules.keys())[0]
            first_rule = rules[first_rule_key]
        src_name = "ANY"
        dst_name = "ANY"
        
        # Determine source name
        if 'source_object_group' in first_rule:
            src_name = normalize_name(first_rule['source_object_group'])
        elif 'source_ip' in first_rule and first_rule['source_ip'] != 'any':
            src_name = normalize_name(first_rule['source_ip'])
        
        # Determine destination name  
        if 'destination_object_group' in first_rule:
            dst_name = normalize_name(first_rule['destination_object_group'])
        elif 'destination_ip' in first_rule and first_rule['destination_ip'] != 'any':
            dst_name = normalize_name(first_rule['destination_ip'])
        
        return f"{src_name} -> {dst_name}"

    def _create_rule_name(self, acl_rule: Dict, destination_zone: str = None, acl_name: str = None, rule_index: int = 0) -> str:
        """Create a descriptive name for a filter policy rule using ACL name and rule index."""
        if acl_name:
            # Clean up ACL name for readability
            clean_acl_name = acl_name.replace('ACL_', '').replace('ACL-', '').replace('_', '-')
            
            # Check if this ACL has multiple rules
            if acl_name in self.acls:
                acl_rule_count = len(self.acls[acl_name].get('rules', []))
                # Only add rule number if there are multiple rules in the ACL and rule_index is not -1
                if acl_rule_count > 1 and rule_index != -1:
                    return f"{clean_acl_name}-{rule_index + 1}"
                else:
                    return clean_acl_name
            else:
                # Fallback if ACL not found
                return clean_acl_name
        else:
            # Fallback to old naming if no ACL name provided
            def normalize_name(name: str) -> str:
                # Remove object-group and service-group from anywhere in the name
                name = name.replace('object-group', '').replace('service-group', '')
                # Clean up object group prefixes for readability
                name = name.replace('NET-', '').replace('HOSTG-', '').replace('HOST-', '').replace('NETG-', '')
                name = name.strip()
                return name.upper() if name else 'GROUP'

            # Start with destination zone if available
            zone_name = destination_zone or 'ANY'
            
            # Determine destination service (host, port, or protocol)
            dst_service = None
            
            # Priority 1: Destination port
            if 'destination_port' in acl_rule and acl_rule['destination_port'] != 'any':
                dst_service = acl_rule['destination_port']
            # Priority 2: Destination object group (likely a service group)
            elif 'destination_object_group' in acl_rule:
                # If the destination object group is literally "object-group", use "GROUP"
                if acl_rule['destination_object_group'] == 'object-group':
                    dst_service = 'GROUP'
                else:
                    # Clean up the name by removing object-group/service-group
                    dst_service = normalize_name(acl_rule['destination_object_group'])
            # Priority 3: Destination IP (if it's a specific host)
            elif 'destination_ip' in acl_rule and acl_rule['destination_ip'] != 'any':
                dst_service = normalize_name(acl_rule['destination_ip'].replace('.', '-'))
            # Priority 4: Protocol
            elif 'protocol' in acl_rule and acl_rule['protocol'] != 'ip':
                dst_service = acl_rule['protocol'].upper()
            else:
                dst_service = 'ANY'

            return f"{zone_name} {dst_service}"
    
    def _get_or_create_ip_identity(self, ip: str) -> str:
        """Get or create an IP identity for a single IP address."""
        # Only create IP identities for valid IP addresses
        if not self._is_valid_ip_address(ip):
            return None
        
        # Check if we already have an identity for this IP
        for identity in self.identities['ip']:
            if identity['name'] == f"IP-{ip.replace('.', '-')}":
                return identity['_id_']
        
        # Create new identity
        identity_id = self._generate_id()
        identity_obj = {
            '_id_': identity_id,
            'name': f"IP-{ip.replace('.', '-')}",
            'friendly_name': '',
            'members': [{'address': ip}]
        }
        self.identities['ip'].append(identity_obj)
        return identity_id
    
    def _is_valid_ip_address(self, ip: str) -> bool:
        """Check if a string is a valid IP address."""
        try:
            import ipaddress
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def _get_or_create_port_identity(self, port: str) -> Optional[str]:
        """Get or create a port identity for a single port."""
        # Check if we already have an identity for this port
        for identity in self.identities['port']:
            if identity['name'] == f"PORT-{port}":
                return identity['_id_']
        
        # Check if this is an object group reference to a SERVICE group only
        if port in self.object_groups and self.object_groups[port].get('type') == 'service':
            # Ensure a port identity exists for this service group
            if port in self.object_group_to_identity:
                return self.object_group_to_identity[port]
        
        # Try to convert to int, if it fails, treat as object group
        try:
            port_num = int(port)
            identity_id = self._generate_id()
            identity_obj = {
                '_id_': identity_id,
                'name': f"PORT-{port}",
                'members': [{'start': port_num, 'end': port_num}]
            }
            self.identities['port'].append(identity_obj)
            return identity_id
        except ValueError:
            # Not a number and not a service object-group → not a valid port identity
            return None
    
    def _get_protocol_identity(self, protocol: str) -> int:
        """Convert protocol name to Cradlepoint protocol identity."""
        protocol_map = {
            'tcp': 6,
            'udp': 17,
            'icmp': 1,
            'icmpv4': 1,
            'icmpv6': 58,
            'ip': 0,
            'ipv4': 0,
            'ipv6': 0,
            'gre': 47,
            'esp': 50,
            'sctp': 132,
            'any': 0
        }
        
        protocol_lower = protocol.lower()
        return protocol_map.get(protocol_lower, 6)  # Default to TCP if unknown

    def _get_protocol_identity_for_rule(self, acl_rule: dict) -> int:
        """Get the appropriate protocol identity for an ACL rule."""
        protocol = acl_rule.get('protocol', 'tcp').lower()
        
        # If the rule uses a service object group, it's likely TCP/UDP traffic
        if 'source_object_group' in acl_rule:
            source_obj_group = acl_rule['source_object_group']
            if source_obj_group and (source_obj_group.startswith('SVC-') or source_obj_group.startswith('SVCG-')):
                # Service object groups typically contain TCP/UDP ports
                # Check if the service group contains UDP ports
                if source_obj_group in self.object_groups:
                    service_group = self.object_groups[source_obj_group]
                    if service_group.get('type') == 'service':
                        # Check if any members are UDP
                        for member in service_group.get('members', []):
                            if 'udp' in str(member).lower():
                                return 17  # UDP
                        return 6  # Default to TCP for service groups
        
        # If the rule uses a destination object group that's a service group
        if 'destination_object_group' in acl_rule:
            dst_obj_group = acl_rule['destination_object_group']
            if dst_obj_group and (dst_obj_group.startswith('SVC-') or dst_obj_group.startswith('SVCG-')):
                # Similar logic for destination service groups
                if dst_obj_group in self.object_groups:
                    service_group = self.object_groups[dst_obj_group]
                    if service_group.get('type') == 'service':
                        for member in service_group.get('members', []):
                            if 'udp' in str(member).lower():
                                return 17  # UDP
                        return 6  # Default to TCP for service groups
        
        # For explicit protocols, use the standard mapping
        if protocol in ['tcp', 'udp', 'icmp', 'icmpv4', 'icmpv6', 'gre', 'esp', 'sctp']:
            return self._get_protocol_identity(protocol)
        
        # For 'ip' protocol, default to TCP (most common for IP traffic)
        if protocol in ['ip', 'ipv4', 'ipv6', 'any']:
            return 6  # TCP
        
        # Default to TCP
        return 6
    
    def _get_protocol_identities_for_service_group(self, service_group_name: str) -> List[int]:
        """Get all protocol identities for a service object group that has both TCP and UDP entries."""
        if service_group_name not in self.object_groups:
            return [6]  # Default to TCP
        
        group = self.object_groups[service_group_name]
        if group['type'] != 'service':
            return [6]  # Default to TCP
        
        # Check if this service group has both TCP and UDP entries
        tcp_ports = set()
        udp_ports = set()
        
        # Parse the original config to find TCP and UDP entries for this service group
        in_service_group = False
        for line in self.config_lines:
            original_line = line
            line = line.strip()
            
            # Start of service group
            if line.startswith(f'object-group service {service_group_name}') or line.startswith(f'object-group service {service_group_name} '):
                in_service_group = True
                continue
            
            # End of service group - stop when we hit a new major section
            elif in_service_group:
                # Stop on comment lines or new sections
                if line.startswith('!'):
                    break
                # Stop on new object-group definitions
                elif line.startswith('object-group '):
                    break
                # Stop on other major sections
                elif (line.startswith('class-map ') or line.startswith('policy-map ') or 
                      line.startswith('zone-pair ') or line.startswith('ip access-list ') or
                      line.startswith('interface ') or line.startswith('router ') or
                      line.startswith('zone security ')):
                    break
                # Skip empty lines and descriptions
                elif not line or line.startswith('description '):
                    continue
                # Parse TCP entries
                elif line.startswith('tcp '):
                    parts = line.split()
                    if len(parts) >= 3 and parts[1] == 'eq':
                        try:
                            port = int(parts[2])
                            tcp_ports.add(port)
                        except ValueError:
                            # Try port name mapping
                            port_name = parts[2]
                            if port_name in self.port_map:
                                tcp_ports.add(self.port_map[port_name])
                # Parse UDP entries
                elif line.startswith('udp '):
                    parts = line.split()
                    if len(parts) >= 3 and parts[1] == 'eq':
                        try:
                            port = int(parts[2])
                            udp_ports.add(port)
                        except ValueError:
                            # Try port name mapping
                            port_name = parts[2]
                            if port_name in self.port_map:
                                udp_ports.add(self.port_map[port_name])
                # Parse TCP-UDP combined entries
                elif line.startswith('tcp-udp '):
                    parts = line.split()
                    if len(parts) >= 3 and parts[1] == 'eq':
                        try:
                            port = int(parts[2])
                            tcp_ports.add(port)
                            udp_ports.add(port)
                        except ValueError:
                            # Try port name mapping
                            port_name = parts[2]
                            if port_name in self.port_map:
                                tcp_ports.add(self.port_map[port_name])
                                udp_ports.add(self.port_map[port_name])
        
        # Return protocols based on what we found
        # If we have both TCP and UDP ports (even if different ports), return both protocols
        if tcp_ports and udp_ports:
            return [6, 17]  # Both TCP and UDP
        elif tcp_ports:
            return [6]  # TCP only
        elif udp_ports:
            return [17]  # UDP only
        else:
            return [6]  # Default to TCP
    
    def create_zone_forwardings(self):
        """Create zone forwardings from zone pairs."""
        for pair_name, pair in self.zone_pairs.items():
            forwarding_id = self._generate_id()
            
            # Find source and destination zone IDs
            src_zone_id = None
            dst_zone_id = None
            
            for zone_id, zone in self.zones.items():
                if zone['name'] == pair['source_zone']:
                    src_zone_id = zone_id
                elif zone['name'] == pair['destination_zone']:
                    dst_zone_id = zone_id
            
            # Determine filter policy
            filter_policy_id = None
            if pair.get('policy_map'):
                # Find the filter policy for this policy map
                for policy_id, policy in self.filter_policies.items():
                    if policy['name'] == pair['policy_map']:
                        filter_policy_id = policy_id
                        break
            
            # Use default deny policy if no specific policy found
            if not filter_policy_id:
                for policy_id, policy in self.filter_policies.items():
                    if policy['name'] == 'Default Deny All':
                        filter_policy_id = policy_id
                        break
            
            self.zone_forwardings[forwarding_id] = {
                '_id_': forwarding_id,
                'src_zone_id': src_zone_id or '',
                'dst_zone_id': dst_zone_id or '',
                'enabled': True,
                'filter_policy_id': filter_policy_id or ''
            }
    
    def create_internet_zone(self):
        """Create an internet zone and forward all other zones to it using default allow all policy."""
        # Create the internet zone
        internet_zone_id = self._generate_id()
        self.zones[internet_zone_id] = {
            '_id_': internet_zone_id,
            'devices': [
                {
                    'trigger_field': 'type',
                    'trigger_group': 'wan',
                    'trigger_neg': False,
                    'trigger_predicate': 'is',
                    'trigger_value': ''
                }
            ],
            'name': self.internet_zone_name
        }
        
        # Find the existing default allow all policy ID
        default_allow_policy_id = None
        for policy_id, policy in self.filter_policies.items():
            if policy['name'] == 'Default Allow All':
                default_allow_policy_id = policy_id
                break
        
        # If no default allow all policy exists, create one
        if not default_allow_policy_id:
            default_allow_policy_id = self._generate_id()
            self.filter_policies[default_allow_policy_id] = {
                '_id_': default_allow_policy_id,
                'name': 'ALLOW ALL',
                'default_action': 'allow',
                'rules': []
            }
        
        # Create forwardings from all other zones to the internet zone
        for zone_id, zone in self.zones.items():
            if zone_id != internet_zone_id:  # Don't create forwarding from internet to itself
                forwarding_id = self._generate_id()
                self.zone_forwardings[forwarding_id] = {
                    '_id_': forwarding_id,
                    'src_zone_id': zone_id,
                    'dst_zone_id': internet_zone_id,
                    'enabled': True,
                    'filter_policy_id': default_allow_policy_id
                }
    
    def generate_cradlepoint_config(self) -> Dict:
        """Generate the complete Cradlepoint configuration."""
        # Parse the configuration first if not already done
        if not self.config_lines:
            self.parse_config()
        
        # Sort filter policies so that "ALLOW ALL" appears first (index 0)
        sorted_filter_policies = {}
        
        # First, add the "ALLOW ALL" policy if it exists
        for policy_id, policy in self.filter_policies.items():
            if policy['name'] == 'ALLOW ALL' or policy['name'] == 'Default Allow All':
                sorted_filter_policies[policy_id] = policy
                break
        
        # Then add all other policies
        for policy_id, policy in self.filter_policies.items():
            if policy['name'] != 'ALLOW ALL' and policy['name'] != 'Default Allow All':
                sorted_filter_policies[policy_id] = policy
        
        return {
            'configuration': [
                {
                    'security': {
                        'zfw': {
                            'zones': self.zones,
                            'filter_policies': sorted_filter_policies,
                            'forwardings': self.zone_forwardings
                        }
                    },
                    'identities': self.identities
                },
                [
                    [
                        "security",
                        "zfw",
                        "forwardings",
                        "00000003-9532-3d3e-968c-e2f54a0cad18"
                    ],
                    [
                        "security",
                        "zfw",
                        "forwardings",
                        "00000002-9532-3d3e-968c-e2f54a0cad18"
                    ],
                    [
                        "security",
                        "zfw",
                        "forwardings",
                        "00000001-9532-3d3e-968c-e2f54a0cad18"
                    ],
                    [
                        "security",
                        "zfw",
                        "forwardings",
                        "00000000-9532-3d3e-968c-e2f54a0cad18"
                    ],
                    [
                        "security",
                        "zfw",
                        "filter_policies",
                        "00000001-77db-3b20-980e-2de482869073"
                    ],
                    [
                        "security",
                        "zfw",
                        "filter_policies",
                        "00000000-77db-3b20-980e-2de482869073"
                    ],
                    [
                        "security",
                        "zfw",
                        "zones",
                        "00000004-695c-3d87-95cb-d0ee2029d0b5"
                    ],
                    [
                        "security",
                        "zfw",
                        "zones",
                        "00000003-695c-3d87-95cb-d0ee2029d0b5"
                    ],
                    [
                        "security",
                        "zfw",
                        "zones",
                        "00000002-695c-3d87-95cb-d0ee2029d0b5"
                    ]
                ]
            ],
            'firmware_version': '7.25.10',
            'firmware_build_timestamp': '2025-05-12T17:01:24+00:00',
            'firmware_multi_image': False,
            'config_encryption_id': None,
            'export_type': 'group'
        }
    
    def validate_against_dtd(self, config: Dict) -> List[str]:
        """Validate the configuration against the DTD."""
        errors = []
        
        # Validate zones
        if 'configuration' in config and len(config['configuration']) > 0:
            zfw = config['configuration'][0].get('security', {}).get('zfw', {})
            
            # Check zones
            zones = zfw.get('zones', {})
            if not zones:
                errors.append("No zones found")
            
            # Check filter policies
            filter_policies = zfw.get('filter_policies', {})
            if not filter_policies:
                errors.append("No filter policies found")
            
            # Check forwardings
            forwardings = zfw.get('forwardings', {})
            if not forwardings:
                errors.append("No zone forwardings found")
            
            # Validate forwarding filter_policy_id references
            for forwarding_id, forwarding in forwardings.items():
                filter_policy_id = forwarding.get('filter_policy_id')
                if filter_policy_id and filter_policy_id not in filter_policies:
                    errors.append(f"Forwarding {forwarding_id} references invalid filter_policy_id: {filter_policy_id}")
        
        return errors
    
    def convert(self) -> Dict:
        """Main conversion method."""
        print("Parsing Cisco configuration...")
        self.parse_config()
        
        print("Generating Cradlepoint configuration...")
        config = self.generate_cradlepoint_config()
        
        print("Validating configuration...")
        errors = self.validate_against_dtd(config)
        if errors:
            print("Validation errors:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("Configuration validation passed!")
        
        return config


def main():
    """Main function for command line usage."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert Cisco configuration to Cradlepoint zone firewall')
    parser.add_argument('config_file', help='Cisco configuration file')
    parser.add_argument('--add-internet-zone', action='store_true', 
                       help='Add DIA zone and forward all zones to it')
    parser.add_argument('--internet-zone-name', default='EXT-Internet',
                       help='Name for the DIA zone (default: EXT-Internet)')
    
    args = parser.parse_args()
    
    try:
        converter = CiscoToCradlepointConverter(
            args.config_file, 
            add_internet_zone=args.add_internet_zone,
            internet_zone_name=args.internet_zone_name
        )
        config = converter.convert()
        
        # Save the configuration
        output_file = args.config_file.replace('.txt', '_cradlepoint.json')
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"Conversion complete! Output saved to: {output_file}")
        
        # Print summary
        zfw = config['configuration'][0]['security']['zfw']
        identities = config['configuration'][0].get('identities', {})
        print(f"\nConfiguration Summary:")
        print(f"  Zones: {len(zfw.get('zones', {}))}")
        print(f"  Filter Policies: {len(zfw.get('filter_policies', {}))}")
        print(f"  Zone Forwardings: {len(zfw.get('forwardings', {}))}")
        print(f"  IP Identities: {len(identities.get('ip', []))}")
        print(f"  Port Identities: {len(identities.get('port', []))}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
