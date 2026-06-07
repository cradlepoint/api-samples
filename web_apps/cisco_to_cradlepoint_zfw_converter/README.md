# Cisco to Cradlepoint Zone Firewall Converter

A comprehensive Python script that converts Cisco router access lists, class maps, object groups, policy maps, and zone-pair configurations to Cradlepoint zone firewall configurations.

## Features

### Supported Cisco Features
- **Access Lists**: Extended IP access lists with complex matching criteria
- **Object Groups**: Network, service, and protocol object groups
- **Class Maps**: Traffic classification with match-any and match-all logic
- **Policy Maps**: Traffic policies with inspect, drop, and pass actions
- **Zone Pairs**: Zone-based security policies
- **Interfaces**: Interface configurations and zone assignments

### Generated Cradlepoint Components
- **Zones**: Security zone definitions
- **Zone Forwardings**: Traffic flow rules between zones
- **Filter Policies**: Firewall rules with source/destination IPs, ports, and protocols

## Installation

### Prerequisites
```bash
pip install netaddr ipaddress
```

### Required Python Packages
- `netaddr`: For IP address and subnet calculations
- `ipaddress`: For IP network operations
- `json`: For configuration output
- `uuid`: For generating unique IDs

## Usage

### Basic Usage
```bash
python cisco_to_cradlepoint_converter.py <cisco_config_file> [output_file]
```

### Examples

#### Convert a Cisco configuration file
```bash
python cisco_to_cradlepoint_converter.py example_cisco_config.txt
```

#### Specify output file
```bash
python cisco_to_cradlepoint_converter.py example_cisco_config.txt cradlepoint_config.json
```

### Command Line Options
- `cisco_config_file`: Path to the Cisco configuration file
- `output_file`: (Optional) Path for the output JSON file (default: `cradlepoint_config.json`)

## Configuration File Format

The script expects a Cisco configuration file with the following supported commands:

### Object Groups
```
object-group network INTERNAL-SERVERS
 host 192.168.1.10
 network 192.168.1.0 255.255.255.0
 range 192.168.1.100 192.168.1.200

object-group service WEB-SERVICES
 tcp 80
 tcp 443
 tcp 8080

object-group protocol SECURE-PROTOCOLS
 tcp
 udp
 esp
```

### Access Lists
```
ip access-list extended INSIDE-TO-OUTSIDE
 permit tcp object-group INTERNAL-SERVERS any eq 80
 permit tcp host 192.168.1.10 any eq 443
 permit icmp any any
 deny ip any any
```

### Class Maps
```
class-map type inspect match-any INSIDE-TRAFFIC
 match access-group name INSIDE-TO-OUTSIDE
 match object-group INTERNAL-SERVERS

class-map type inspect match-all WEB-TRAFFIC
 match access-group name INSIDE-TO-OUTSIDE
 match object-group WEB-SERVICES
```

### Policy Maps
```
policy-map INSIDE-TO-OUTSIDE-POLICY
 class INSIDE-TRAFFIC
  inspect tcp
  inspect udp
  inspect icmp
 class class-default
  drop
```

### Zone Pairs
```
zone-pair security INSIDE-TO-OUTSIDE source INSIDE destination OUTSIDE
 service-policy type inspect INSIDE-TO-OUTSIDE-POLICY
```

### Interface Assignments
```
interface GigabitEthernet0/0
 description Inside Network
 ip address 192.168.1.1 255.255.255.0
 zone-member security INSIDE
```

## Output Format

The script generates two types of output:

### 1. CLI Commands
Cradlepoint CLI commands that can be executed directly:
```
post /config/security/zfw/zones/ {"_id_": "...", "name": "trusted", ...}
post /config/security/zfw/zone_forwardings/ {"_id_": "...", "src_zone": "trusted", ...}
post /config/security/zfw/filter_policies/ {"_id_": "...", "name": "INSIDE-TO-OUTSIDE", ...}
```

### 2. JSON Configuration
Complete configuration in JSON format for programmatic use:
```json
{
  "zones": {
    "trusted": {
      "_id_": "uuid",
      "name": "trusted",
      "description": "Internal trusted network",
      "interfaces": ["GigabitEthernet0/0"]
    }
  },
  "zone_forwardings": {
    "forwarding_1": {
      "_id_": "uuid",
      "name": "Forwarding_INSIDE-TO-OUTSIDE",
      "src_zone": "trusted",
      "dst_zone": "untrusted",
      "filter_policy": "INSIDE-TO-OUTSIDE-POLICY",
      "enabled": true
    }
  },
  "filter_policies": {
    "INSIDE-TO-OUTSIDE": {
      "_id_": "uuid",
      "name": "INSIDE-TO-OUTSIDE",
      "default_action": "deny",
      "rules": [...]
    }
  }
}
```

## Zone Mapping

The script automatically maps Cisco zones to Cradlepoint zones:

| Cisco Zone | Cradlepoint Zone | Description |
|------------|------------------|-------------|
| INSIDE | trusted | Internal trusted network |
| OUTSIDE | untrusted | External untrusted network |
| DMZ | dmz | DMZ network |
| Custom zones | Custom names | Preserved as-is |

## Protocol and Port Mapping

### Supported Protocols
- `tcp` → Protocol 6
- `udp` → Protocol 17
- `icmp` → Protocol 1
- `gre` → Protocol 47
- `esp` → Protocol 50
- `ah` → Protocol 51
- `ospf` → Protocol 89

### Port Name Translation
The script includes comprehensive port name to number translation:
- `http` → 80
- `https` → 443
- `ssh` → 22
- `telnet` → 23
- `ftp` → 21
- `smtp` → 25
- `dns` → 53
- `ntp` → 123
- And many more...

## Advanced Features

### Object Group Resolution
Object groups are automatically resolved to individual IP addresses and ports:
```
object-group network INTERNAL-SERVERS
 host 192.168.1.10
 host 192.168.1.11
```
Becomes:
```json
[
  {"identity": "192.168.1.10/32"},
  {"identity": "192.168.1.11/32"}
]
```

### Complex ACL Support
The script handles complex ACL rules including:
- Object group references
- Port ranges (`range 1024 65535`)
- Greater than ports (`gt 1024`)
- Multiple protocols
- ICMP types

### Zone-Pair Priority
Zone-pair configurations take precedence over class-map based zone forwardings for more accurate traffic flow mapping.

## Error Handling

The script includes comprehensive error handling:
- File not found errors
- Invalid configuration syntax
- Missing object group references
- Malformed IP addresses
- Invalid port specifications

## Examples

### Simple Web Server Access
```cisco
ip access-list extended WEB-ACCESS
 permit tcp any host 192.168.1.10 eq 80
 permit tcp any host 192.168.1.10 eq 443
 deny ip any any
```

### Complex Object Group Usage
```cisco
object-group network WEB-SERVERS
 host 192.168.1.10
 host 192.168.1.11
 network 192.168.1.0 255.255.255.0

ip access-list extended WEB-ACCESS
 permit tcp any object-group WEB-SERVERS eq 80
 permit tcp any object-group WEB-SERVERS eq 443
 deny ip any any
```

### Zone-Based Security
```cisco
zone-pair security INSIDE-TO-OUTSIDE source INSIDE destination OUTSIDE
 service-policy type inspect INSIDE-TO-OUTSIDE-POLICY
```

