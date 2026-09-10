# 🛡️ kisa_harden : AWS EC2 Linux/Unix KISA 취약점 점검 & 하드닝 Ansible 프로젝트

한국인터넷진흥원(KISA) **2026 주요정보통신기반시설 기술적 취약점 분석·평가 방법 상세가이드 (U-01 ~ U-67)** 및 [`SHyoJun/linux-vulnerability-check`](https://github.com/SHyoJun/linux-vulnerability-check) 기준을 완벽하게 준수하는 **AWS EC2 다중 OS 보안 진단 및 자동 하드닝(조치) Ansible Playbook 프로젝트 (`kisa_harden`)**입니다.

---

## 🚀 지원 운영체제 및 클라우드 환경

- **클라우드 환경**: AWS EC2 (VPC, Security Group, Amazon Time Sync Service 연동)
- **지원 운영체제 (8종)**:
  - **RedHat Family**: Amazon Linux 2023 (AL2023), Fedora, RHEL (8/9), Rocky Linux (8/9), CentOS (7/8/9 Stream)
  - **Debian Family**: Ubuntu (20.04 / 22.04 / 24.04 LTS), Debian (11 / 12)
  - **BSD Family**: FreeBSD (13 / 14)

---

## 📂 프로젝트 구조

```text
.
├── ansible.cfg                          # 실행 성능 및 출력 최적화 설정
├── inventory/
│   ├── hosts.ini                        # OS별 호스트 그룹 인벤토리
│   └── aws_ec2.yml                      # AWS EC2 동적 인벤토리 설정
├── group_vars/
│   ├── all.yml                          # KISA 전역 보안 기준 파라미터 (임계값, 타임아웃 등)
│   ├── redhat_family.yml                # RHEL, AL2023, Fedora, Rocky, CentOS 설정
│   ├── debian_family.yml                # Ubuntu, Debian 설정
│   └── freebsd.yml                      # FreeBSD 전용 설정
├── roles/
│   ├── kisa_harden/                     # [조치] 보안 하드닝 롤 (U-01 ~ U-67)
│   │   ├── defaults/main.yml
│   │   ├── handlers/main.yml            # sshd, chrony, rsyslog 등 서비스 핸들러
│   │   ├── tasks/
│   │   │   ├── main.yml                 # 5대 도메인 오케스트레이션
│   │   │   ├── 01_account/              # U-01 ~ U-13 (계정 관리)
│   │   │   ├── 02_filesystem/           # U-14 ~ U-33 (파일/디렉터리 관리)
│   │   │   ├── 03_services/             # U-34 ~ U-63 (서비스 관리)
│   │   │   ├── 04_patch/                # U-64 (패치 관리)
│   │   │   └── 05_log/                  # U-65 ~ U-67 (로그/시간 동기화)
│   │   └── templates/                   # motd, chrony, timeout, pwquality 등 템플릿
│   └── kisa_audit/                      # [점검] 취약점 진단 및 리포트 자동 생성 롤
├── scripts/
│   └── generate_hosts_ini.py            # EC2 인스턴스 조회 기반 hosts.ini 자동 생성 도구
├── site.yml                             # 보안 하드닝(조치) 실행 플레이북
├── audit.yml                            # 보안 진단(점검) 실행 플레이북
└── README.md                            # 사용 설명서
```

---

## ⚙️ 인벤토리 구성 방법 (2가지 방식)

### 방식 1. 스크립트로 `hosts.ini` 자동 생성 (가장 간편한 방법) 🌟
제공된 [scripts/generate_hosts_ini.py](file:///home/keikun/project/ansible/scripts/generate_hosts_ini.py)를 실행하여 AWS EC2에서 실행 중인 인스턴스를 실시간으로 조회하고 `hosts.ini`를 자동 생성합니다.

```bash
# 기본 실행 (ap-northeast-2 리전, 프라이빗 IP 기준)
python3 scripts/generate_hosts_ini.py

# 특정 리전 및 퍼블릭 IP 사용 옵션
python3 scripts/generate_hosts_ini.py --region ap-northeast-2 --public-ip
```

> **태그 팁**: EC2 인스턴스의 Tag에 `OS: amazon_linux`, `OS: ubuntu`, `OS: rocky` 등을 부여해두면 해당 OS 그룹에 자동으로 배치됩니다. (Name 태그에 os명이 포함되어 있어도 자동 판별)

---

### 방식 2. Ansible AWS EC2 동적 인벤토리 (Dynamic Inventory)
파일을 수동으로 생성할 필요 없이 Ansible이 AWS API를 통해 실시간으로 인스턴스 목록을 가져와 실행합니다.

```bash
# 1. amazon.aws 컬렉션 및 boto3 설치 (최초 1회)
ansible-galaxy collection install amazon.aws
pip install boto3 botocore

# 2. 동적 인벤토리로 점검/하드닝 실행 (inventory/aws_ec2.yml 사용)
ansible-playbook -i inventory/aws_ec2.yml site.yml
```

---

## 💡 사용 방법 (Usage)

### 1. 보안 진단 (Audit Mode) - 시스템 변경 없이 취약점 점검
대상 서버의 취약점 상태를 점검하고 `./reports/` 디렉토리에 마크다운 진단 보고서를 생성합니다.
```bash
ansible-playbook -i inventory/hosts.ini audit.yml
```

### 2. 전체 보안 하드닝 (Remediation Mode) - U-01 ~ U-67 자동 조치
가이드라인 기준에 맞추어 모든 보안 설정을 안전하게 적용합니다.
```bash
ansible-playbook -i inventory/hosts.ini site.yml
```

### 3. 특정 취약점 ID 또는 영역별 선택 실행 (Tag 활용)
원하는 항목의 태그를 지정하여 특정 항목만 선택적으로 조치할 수 있습니다.

```bash
# U-01 (SSH root 원격 접속 제한)만 실행
ansible-playbook -i inventory/hosts.ini site.yml --tags "U-01"

# 계정 관리(U-01 ~ U-13) 영역만 일괄 실행
ansible-playbook -i inventory/hosts.ini site.yml --tags "account"

# 시간 동기화(U-65: AWS NTP) 및 로그 관리만 실행
ansible-playbook -i inventory/hosts.ini site.yml --tags "log"

### 4. Python 3.14 설치 및 업그레이드 (선택 사항)
대상 서버들에 Python 3.14 및 최신 pip 환경을 안전하게 컴파일/설치합니다 (`altinstall` 방식을 사용하여 시스템 기본 패키지 관리자 충돌 방지).
```bash
# 전체 호스트에 Python 3.14 설치
ansible-playbook -i inventory/hosts.ini upgrade_python.yml

# 특정 호스트/그룹에만 설치
ansible-playbook -i inventory/hosts.ini upgrade_python.yml -e "target_hosts=amazon_linux"
```

---

## 📋 항목별(U-01 ~ U-67) 대응 매핑 및 조치 내역

| ID | 도메인 | 항목명 | 주요 조치 내용 및 태그 |
|---|---|---|---|
| **U-01** | 계정 관리 | root 계정 원격 접속 제한 | `PermitRootLogin no` 강제, `securetty` pts 제한 (`--tags "U-01"`) |
| **U-02** | 계정 관리 | 비밀번호 복잡성 설정 | `pam_pwquality` 설치 및 minlen=8, 3종 이상 혼용 규칙 적용 (`--tags "U-02"`) |
| **U-03** | 계정 관리 | 계정 잠금 임계값 설정 | `pam_faillock` deny=5, unlock_time=900 설정 (`--tags "U-03"`) |
| **U-04** | 계정 관리 | 비밀번호 파일 보호 | `/etc/passwd` shadow 플래그 및 `/etc/shadow` 무결성 검증 (`--tags "U-04"`) |
| **U-05** | 계정 관리 | root 이외 UID 0 금지 | UID 0 중복 계정 검출 및 비인가 계정 차단 (`--tags "U-05"`) |
| **U-06** | 계정 관리 | su 기능 제한 | `pam_wheel.so` 활성화 및 wheel/sudo 그룹 제어 (`--tags "U-06"`) |
| **U-07~11** | 계정 관리 | 기본 계정/쉘/중복UID 관리 | 미사용 계정 잠금, 시스템 계정 nologin 쉘 지정 (`--tags "account"`) |
| **U-12** | 계정 관리 | 세션 종료 시간 설정 | `TMOUT=600` (10분) 강제 적용 (`--tags "U-12"`) |
| **U-13** | 계정 관리 | 암호화 알고리즘 | `login.defs` 내 `ENCRYPT_METHOD SHA512` 설정 (`--tags "U-13"`) |
| **U-14~22** | 파일 관리 | 중요 파일 소유자/권한 | `/etc/passwd`(644), `/etc/shadow`(400), `/etc/hosts`(644), `/etc/services`(644) (`--tags "filesystem"`) |
| **U-23~26** | 파일 관리 | 특수 권한/소유자 없는 파일 | 비인가 SUID 제거, World Writable/장치 파일 점검 (`--tags "filesystem"`) |
| **U-27** | 파일 관리 | r-command 금지 | `hosts.equiv`, `~/.rhosts` 파일 강제 삭제 (`--tags "U-27"`) |
| **U-28** | 파일 관리 | 접속 IP/포트 제한 | `/etc/hosts.deny` (ALL: ALL) 및 hosts.allow 설정 (`--tags "U-28"`) |
| **U-29~33** | 파일 관리 | UMASK & 홈디렉터리 권한 | `UMASK 022` 강제, `/home/*` 타인 쓰기 권한 제거 (`--tags "U-30, U-31"`) |
| **U-34~44** | 서비스 관리 | 불필요 레거시 서비스 비활성화 | finger, rsh, rlogin, NFS, autofs, rpcbind, tftp, talk 중지/마스킹 (`--tags "services"`) |
| **U-45~51** | 서비스 관리 | 메일 및 DNS 보안 | Sendmail `restrictqrun`, DNS `allow-transfer { none; };` 적용 (`--tags "services"`) |
| **U-52** | 서비스 관리 | Telnet 서비스 비활성화 | telnet socket/service 중지 및 마스킹 (`--tags "U-52"`) |
| **U-53~57** | 서비스 관리 | FTP 서비스 보안 | Anonymous 차단, FTP 배너 숨김, `/etc/ftpusers` root 차단 (`--tags "ftp"`) |
| **U-58~61** | 서비스 관리 | SNMP 보안 | snmpd 비활성화, 기본 community string 제거 (`--tags "snmp"`) |
| **U-62** | 서비스 관리 | 로그인 경고 배너 | `/etc/motd`, `/etc/issue` 법적 경고 메시지 배포 (`--tags "U-62"`) |
| **U-63** | 서비스 관리 | sudo 접근 관리 | `/etc/sudoers` 권한 440 설정 및 문법 자동 검증 (`--tags "U-63"`) |
| **U-64** | 패치 관리 | 보안 패치 적용 | `dnf/yum --security` 또는 `apt upgrade` 지원 (`--tags "U-64"`) |
| **U-65** | 로그 관리 | NTP 시각 동기화 | AWS EC2 전용 Amazon Time Sync Service (`169.254.169.123`) 동기화 (`--tags "U-65"`) |
| **U-66~67** | 로그 관리 | 시스템 로깅 & 권한 | rsyslog 활성화 및 `/var/log` 권한 755 이하 조정 (`--tags "log"`) |

---

## 🔒 AWS EC2 환경 특화 보안 고려사항

1. **Amazon Time Sync Service**:
   - `169.254.169.123` 링크 로컬 NTP 서버를 활용하여 외부 인터넷 게이트웨이나 NAT 게이트웨이 없이도 정확하고 안전한 시각 동기화 제공
2. **SSH Key 인증 및 Root 차단**:
   - AWS 기본 관리 계정(`ec2-user`, `ubuntu`, `rocky` 등)의 sudo 권한을 안전하게 유지하면서 직접 root SSH 원격 로그인을 차단
3. **OS별 PAM 및 패키지 매니저 완벽 호환**:
   - RedHat 8/9, AL2023, Fedora의 `authselect`/`dnf` 환경과 Debian/Ubuntu의 `apt`/`pam-auth-update` 환경을 자동 감지하여 오류 없이 처리
