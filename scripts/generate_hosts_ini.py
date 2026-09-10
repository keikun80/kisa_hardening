#!/usr/bin/env python3
"""
AWS EC2 인스턴스를 조회하여 Ansible용 inventory/hosts.ini를 자동 생성하는 스크립트
"""

import os
import sys
import json
import subprocess
import argparse

# OS별 기본 SSH 사용자명 매핑
DEFAULT_SSH_USERS = {
    "amazon_linux": "ec2-user",
    "al2023": "ec2-user",
    "fedora": "fedora",
    "rhel": "ec2-user",
    "rocky": "rocky",
    "centos": "centos",
    "ubuntu": "ubuntu",
    "debian": "admin",
    "freebsd": "ec2-user",
}

def detect_os_group(tags, image_name=""):
    """EC2 태그 또는 AMI 이름에서 OS 그룹을 판별"""
    # 1. 태그 확인 (OS, os, Distro, distro 등)
    for tag_key in ["OS", "os", "Distro", "distro", "Platform", "platform"]:
        if tag_key in tags:
            val = tags[tag_key].lower()
            if "amazon" in val or "al2023" in val:
                return "amazon_linux"
            if "fedora" in val:
                return "fedora"
            if "rhel" in val or "redhat" in val:
                return "rhel"
            if "rocky" in val:
                return "rocky"
            if "centos" in val:
                return "centos"
            if "ubuntu" in val:
                return "ubuntu"
            if "debian" in val:
                return "debian"
            if "freebsd" in val:
                return "freebsd"

    # 2. Name 태그 기준 추론
    name = tags.get("Name", "").lower()
    for os_name in ["amazon_linux", "al2023", "fedora", "rhel", "rocky", "centos", "ubuntu", "debian", "freebsd"]:
        if os_name in name:
            return "amazon_linux" if os_name == "al2023" else os_name

    # 3. AMI 이름 추론
    img = image_name.lower()
    if "amzn2023" in img or "amazon" in img:
        return "amazon_linux"
    if "ubuntu" in img:
        return "ubuntu"
    if "debian" in img:
        return "debian"
    if "fedora" in img:
        return "fedora"
    if "rocky" in img:
        return "rocky"
    if "rhel" in img:
        return "rhel"
    if "centos" in img:
        return "centos"
    if "freebsd" in img:
        return "freebsd"

    return "amazon_linux"  # 기본값


def fetch_ec2_instances(region="ap-northeast-2", use_private_ip=True):
    """AWS CLI를 통해 실행 중인 EC2 인스턴스 정보 수집"""
    cmd = [
        "aws", "ec2", "describe-instances",
        "--region", region,
        "--filters", "Name=instance-state-name,Values=running",
        "--output", "json"
    ]
    try:
        res = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        data = json.loads(res.stdout)
    except Exception as e:
        print(f"[ERROR] AWS CLI 실행 실패: {e}", file=sys.stderr)
        print("AWS 자격증명(Credentials) 및 AWS CLI 설치 여부를 확인하세요.", file=sys.stderr)
        sys.exit(1)

    instances_by_group = {
        "amazon_linux": [],
        "fedora": [],
        "rhel": [],
        "rocky": [],
        "centos": [],
        "ubuntu": [],
        "debian": [],
        "freebsd": []
    }

    for reservation in data.get("Reservations", []):
        for inst in reservation.get("Instances", []):
            tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
            name = tags.get("Name", inst["InstanceId"])
            ip = inst.get("PrivateIpAddress") if use_private_ip else (inst.get("PublicIpAddress") or inst.get("PrivateIpAddress"))

            if not ip:
                continue

            group = detect_os_group(tags)
            user = DEFAULT_SSH_USERS.get(group, "ec2-user")
            
            line = f"{name} ansible_host={ip} ansible_user={user}"
            if group == "freebsd":
                line += " ansible_python_interpreter=/usr/local/bin/python3"

            instances_by_group[group].append(line)

    return instances_by_group


def generate_ini_content(groups):
    """hosts.ini 파일 내용 생성"""
    lines = [
        "# ==================================================================",
        "# Auto-generated hosts.ini from AWS EC2 Instances",
        "# ==================================================================",
        "",
        "[all:vars]",
        "ansible_ssh_common_args='-o StrictHostKeyChecking=no'",
        "# ansible_ssh_private_key_file=~/.ssh/your-aws-key.pem",
        "",
        "# ==========================================",
        "# RedHat 계열",
        "# ==========================================",
        "[amazon_linux]",
    ]
    lines.extend(groups["amazon_linux"] if groups["amazon_linux"] else ["# (No running instances found)"])
    lines.extend(["", "[fedora]"])
    lines.extend(groups["fedora"] if groups["fedora"] else ["# (No running instances found)"])
    lines.extend(["", "[rhel]"])
    lines.extend(groups["rhel"] if groups["rhel"] else ["# (No running instances found)"])
    lines.extend(["", "[rocky]"])
    lines.extend(groups["rocky"] if groups["rocky"] else ["# (No running instances found)"])
    lines.extend(["", "[centos]"])
    lines.extend(groups["centos"] if groups["centos"] else ["# (No running instances found)"])
    lines.extend([
        "",
        "[redhat_family:children]",
        "amazon_linux",
        "fedora",
        "rhel",
        "rocky",
        "centos",
        "",
        "# ==========================================",
        "# Debian 계열",
        "# ==========================================",
        "[ubuntu]"
    ])
    lines.extend(groups["ubuntu"] if groups["ubuntu"] else ["# (No running instances found)"])
    lines.extend(["", "[debian]"])
    lines.extend(groups["debian"] if groups["debian"] else ["# (No running instances found)"])
    lines.extend([
        "",
        "[debian_family:children]",
        "ubuntu",
        "debian",
        "",
        "# ==========================================",
        "# BSD 계열",
        "# ==========================================",
        "[freebsd]"
    ])
    lines.extend(groups["freebsd"] if groups["freebsd"] else ["# (No running instances found)"])
    lines.extend([
        "",
        "[linux_servers:children]",
        "redhat_family",
        "debian_family",
        "",
        "[target_servers:children]",
        "linux_servers",
        "freebsd",
        ""
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="AWS EC2에서 Ansible hosts.ini 자동 생성")
    parser.add_argument("--region", default="ap-northeast-2", help="AWS Region (기본값: ap-northeast-2)")
    parser.add_argument("--public-ip", action="store_true", help="프라이빗 IP 대신 퍼블릭 IP 사용")
    parser.add_argument("--output", default="inventory/hosts.ini", help="출력 파일 경로 (기본값: inventory/hosts.ini)")
    args = parser.parse_args()

    print(f"[*] AWS EC2 인스턴스 검색 중... (Region: {args.region})")
    groups = fetch_ec2_instances(region=args.region, use_private_ip=not args.public_ip)
    content = generate_ini_content(groups)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[+] 성공: {args.output} 파일이 성공적으로 생성되었습니다.")


if __name__ == "__main__":
    main()
