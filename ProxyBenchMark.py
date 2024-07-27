import threading
import pycurl
import time
import json
import pycountry
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich.live import Live
from datetime import datetime

class Tool(object):
    def __init__(self):
        self.proxy_host = ""
        self.proxy_port = ""
        self.proxy_username = ""
        self.proxy_password = ""

        self.x = 0
        self.threads = 0
        self.repeating_ip_count = 0
        self.unique_ip_count = 0
        self.ips = {}
        self.countries = defaultdict(int)
        self.response_times = []
        self.lock = threading.Lock()
        self.error = 0
        self.datacenter_leaks = 0
        self.mobile_proxies = 0
        self.residential_proxies = 0
        self.unknown_network = 0
        self.console = Console()
        self.log_file = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self.initialize_log()

    def initialize_log(self):
        with open(self.log_file, "w") as log:
            log.write(f"Log started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    def fetch_ip_info(self, ip, curl):
        try:
            curl.setopt(curl.URL, "https://ipinfo.io/widget/demo/"+str(ip))
            curl.setopt(curl.HTTPHEADER, ["Connection: close"])
            return curl.perform_rs()
        except Exception as e:
            return str(e)

    def fetch_ip(self, curl):
        try:
            curl.setopt(curl.URL, "https://ipinfo.io/json")
            curl.setopt(curl.SSL_VERIFYHOST, 0)
            curl.setopt(curl.SSL_VERIFYPEER, 0)
            curl.setopt(curl.TIMEOUT_MS, 60000)
            curl.setopt(curl.PROXY, f"{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}")
            start_time = time.time()
            response = curl.perform_rs()
            end_time = time.time()
            response_time = end_time - start_time
            return json.loads(response)["ip"], response_time
        except Exception as e:
            return str(e), 0

    def run(self):
        while True:
            curl = pycurl.Curl()
            ip, response_time = self.fetch_ip(curl)
            response = self.fetch_ip_info(ip, curl)
            try:
                with self.lock:
                    data = json.loads(response)
                    country_code = data["data"]["country"]
                    country = pycountry.countries.get(alpha_2=country_code).name
                    self.response_times.append(response_time)
                    self.x += 1
                    if ip in self.ips:
                        self.repeating_ip_count += 1
                        self.ips[ip] += 1
                    else:
                        self.ips[ip] = 1
                        self.unique_ip_count += 1
                        self.countries[country] += 1
                        asn_type = data["data"]["asn"]["type"]
                        if asn_type == "hosting":
                            self.datacenter_leaks += 1
                        elif asn_type == "isp":
                            self.residential_proxies += 1
                        elif asn_type == "mobile":
                            self.mobile_proxies += 1
                        else:
                            #print("Asn type", asn_type, ip)
                            self.unknown_network += 1
            except Exception as e:
                self.error += 1
                #print("Error", str(e), response)

    def log_summary(self):
        with self.lock:
            avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
            lowest_response_time = min(self.response_times) if self.response_times else 0
            highest_response_time = max(self.response_times) if self.response_times else 0
            total_ips = sum(self.countries.values())
            sorted_countries = sorted(self.countries.items(), key=lambda item: item[1], reverse=True)
            country_distribution = "\n".join(
                [f"{country}: {count} ({count / total_ips * 100:.2f}%)" for country, count in sorted_countries]
            )
            with open(self.log_file, "w") as log:
                log.write(f"Proxy: {self.proxy_host}\n")
                log.write(f"Total Requests Sent: {self.x}\n")
                log.write(f"Unique IPs: {self.unique_ip_count}\n")
                log.write(f"Repeated IPs: {self.repeating_ip_count}\n")
                log.write(f"Residential Network: {self.residential_proxies}\n")
                log.write(f"Mobile Network: {self.mobile_proxies}\n")
                log.write(f"Datacenter Network: {self.datacenter_leaks}\n")
                log.write(f"Unknown Network: {self.unknown_network}\n")
                log.write(f"Error: {self.error}\n")
                log.write(f"Average Response Time: {avg_response_time:.2f} seconds\n")
                log.write(f"Lowest Response Time: {lowest_response_time:.2f} seconds\n")
                log.write(f"Highest Response Time: {highest_response_time:.2f} seconds\n\n")
                log.write(f"Country Distribution:\n{country_distribution}\n")

    def get_table(self):
        table = Table()
        table.add_column("Metric", justify="right", style="cyan", no_wrap=True)
        table.add_column("Value", justify="left", style="magenta")
        table.add_row("Proxy", self.proxy_host)
        table.add_row("Total Requests", str(self.x))
        table.add_row("Unique IPs", str(self.unique_ip_count))
        table.add_row("Repeated IPs", str(self.repeating_ip_count))
        table.add_row("Residential Network", str(self.residential_proxies))
        table.add_row("Mobile Network", str(self.mobile_proxies))
        table.add_row("Datacenter Network", str(self.datacenter_leaks))
        table.add_row("Unknown Network", str(self.unknown_network))
        table.add_row("Error", str(self.error))
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        table.add_row("Average Response Time", f"{avg_response_time:.2f} seconds")

        lowest_response_time = min(self.response_times) if self.response_times else 0
        table.add_row("Lowest Response Time", f"{lowest_response_time:.2f} seconds")

        highest_response_time = max(self.response_times) if self.response_times else 0
        table.add_row("Highest Response Time", f"{highest_response_time:.2f} seconds")

        total_ips = sum(self.countries.values())
        sorted_countries = sorted(self.countries.items(), key=lambda item: item[1], reverse=True)
        country_distribution = "\n".join(
            [f"{country}: {count} ({count / total_ips * 100:.2f}%)" for country, count in sorted_countries]
        )
        #table.add_row("Country Distribution", country_distribution)
        return table

    def display_stats(self):
        with Live(self.get_table(), refresh_per_second=1, console=self.console) as live:
            while True:
                time.sleep(1)
                live.update(self.get_table())

    def periodic_log_summary(self):
        while True:
            time.sleep(3)
            self.log_summary()

tool = Tool()
print("Rotating Proxy Benchmark Tool")
threads = input("[Threads]: ")
threading.Thread(target=(tool.display_stats)).start()
threading.Thread(target=(tool.periodic_log_summary)).start()
for i in range(int(threads)):
    tool.threads += 1
    threading.Thread(target=(tool.run)).start()
