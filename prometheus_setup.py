import os
import subprocess
import sys
import yaml

def check_python_version():
    if sys.version_info < (3, 6):
        print("[ERROR] Python 3.6 or higher is required.")
        sys.exit(1)

def check_dependencies():
    required_tools = ["wget", "tar", "nano"]
    for tool in required_tools:
        if subprocess.call(f"which {tool}", shell=True) != 0:
            print(f"[ERROR] {tool} is not installed. Please install it and try again.")
            sys.exit(1)

def group_exists(group_name):
    """Check if a group exists."""
    return subprocess.call(f"getent group {group_name}", shell=True) == 0

def user_exists(user_name):
    """Check if a user exists."""
    return subprocess.call(f"id -u {user_name}", shell=True) == 0

def install_prometheus():
    try:
        print("[INFO] Installing Prometheus...")

        # Check and create group and user
        if not group_exists("prometheus"):
            subprocess.run(["sudo", "groupadd", "--system", "prometheus"], check=True)
        else:
            print("[INFO] Group 'prometheus' already exists.")

        if not user_exists("prometheus"):
            subprocess.run(["sudo", "useradd", "-s", "/sbin/nologin", "--system", "-g", "prometheus", "prometheus"], check=True)
        else:
            print("[INFO] User 'prometheus' already exists.")

        # Create directories
        subprocess.run(["sudo", "mkdir", "-p", "/etc/prometheus", "/var/lib/prometheus"], check=True)

        # Download and extract Prometheus
        version = "2.43.0"
        filename = f"prometheus-{version}.linux-amd64.tar.gz"
        url = f"https://github.com/prometheus/prometheus/releases/download/v{version}/{filename}"
        subprocess.run(["wget", url], check=True)
        subprocess.run(["tar", "-xvzf", filename], check=True)

        # Move binaries and configuration files
        folder = f"prometheus-{version}.linux-amd64"
        subprocess.run(["sudo", "mv", f"{folder}/prometheus", "/usr/local/bin/"], check=True)
        subprocess.run(["sudo", "mv", f"{folder}/promtool", "/usr/local/bin/"], check=True)
        subprocess.run(["sudo", "mv", f"{folder}/consoles", "/etc/prometheus/"], check=True)
        subprocess.run(["sudo", "mv", f"{folder}/console_libraries", "/etc/prometheus/"], check=True)
        subprocess.run(["sudo", "mv", f"{folder}/prometheus.yml", "/etc/prometheus/"], check=True)

        # Set ownership
        subprocess.run(["sudo", "chown", "-R", "prometheus:prometheus", "/etc/prometheus", "/var/lib/prometheus"], check=True)

        # Create systemd service
        service_content = """[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/prometheus \\
    --config.file /etc/prometheus/prometheus.yml \\
    --storage.tsdb.path /var/lib/prometheus/ \\
    --web.console.templates=/etc/prometheus/consoles \\
    --web.console.libraries=/etc/prometheus/console_libraries
Restart=always

[Install]
WantedBy=multi-user.target
"""
        with open("/tmp/prometheus.service", "w") as f:
            f.write(service_content)
        subprocess.run(["sudo", "mv", "/tmp/prometheus.service", "/etc/systemd/system/prometheus.service"], check=True)

        # Reload and start Prometheus service
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "enable", "prometheus"], check=True)
        subprocess.run(["sudo", "systemctl", "start", "prometheus"], check=True)

        print("[INFO] Prometheus installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to install Prometheus: {e}")

def add_targets_to_yml():
    try:
        print("[INFO] Adding targets to Prometheus configuration...")
        yml_file = "/etc/prometheus/prometheus.yml"
        
        # Read the existing configuration
        with open(yml_file, "r") as f:
            config = yaml.safe_load(f)

        # Prompt for the new target
        target = input("Enter the target to add (e.g., '172.31.15.155:9100'): ")
        new_target = f"{target}"

        # Find or create scrape_configs
        scrape_configs = config.get("scrape_configs", [])
        for job in scrape_configs:
            if job.get("job_name") == "prometheus":
                static_configs = job.setdefault("static_configs", [])
                if static_configs:
                    static_configs[0]["targets"].append(new_target)
                else:
                    static_configs.append({"targets": [new_target]})
                break
        else:
            # Add a new job if "prometheus" job_name does not exist
            scrape_configs.append({
                "job_name": "prometheus",
                "static_configs": [{"targets": [new_target]}]
            })
        config["scrape_configs"] = scrape_configs

        # Write the updated configuration back
        with open("/tmp/prometheus.yml", "w") as f:
            yaml.dump(config, f)
        subprocess.run(["sudo", "mv", "/tmp/prometheus.yml", yml_file], check=True)

        print(f"[INFO] Target '{new_target}' added successfully.")

        # Restart Prometheus to apply changes
        print("[INFO] Restarting Prometheus service...")
        subprocess.run(["sudo", "systemctl", "restart", "prometheus"], check=True)
        print("[INFO] Prometheus service restarted successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to add target: {e}")

def remove_prometheus():
    try:
        print("[INFO] Removing Prometheus...")
        subprocess.run(["sudo", "systemctl", "stop", "prometheus"], check=True)
        subprocess.run(["sudo", "systemctl", "disable", "prometheus"], check=True)
        subprocess.run(["sudo", "rm", "-rf", "/usr/local/bin/prometheus", "/var/lib/prometheus", "/etc/prometheus"], check=True)
        subprocess.run(["sudo", "rm", "/etc/systemd/system/prometheus.service"], check=True)
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        print("[INFO] Prometheus removed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to remove Prometheus: {e}")

def systemctl_status():
    try:
        print("[INFO] Checking Prometheus service status...")
        subprocess.run(["sudo", "systemctl", "status", "prometheus"])
    except Exception as e:
        print(f"[ERROR] Unable to fetch Prometheus status: {e}")

def main():
    check_python_version()
    check_dependencies()

    while True:
        print("\nSelect an option:")
        print("1. Install Prometheus")
        print("2. Add Targets to Prometheus Configuration")
        print("3. Remove Prometheus")
        print("4. Check Prometheus Service Status")
        print("0. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            install_prometheus()
        elif choice == "2":
            add_targets_to_yml()
        elif choice == "3":
            remove_prometheus()
        elif choice == "4":
            systemctl_status()
        elif choice == "0":
            print("[INFO] Exiting...")
            break
        else:
            print("[ERROR] Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
