
# !/usr/bin/env python3
"""
Multi-Region Deployment Controller with Rollback

Safely deploys services across multiple regions with health checks
and automatic rollback on failure.
"""

import requests
import time
import sys
import subprocess
import os


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class Deployer:
    def __init__(self, version, failure_rate=0.0):
        self.version = version
        self.failure_rate = failure_rate
        self.deployed_regions = []
        self.current_version = self._detect_current_version()  # ← Changed this
        self.regions = [
            'region-us-west',
            'region-us-east',
            'region-eu-west',
            'region-ap-south'
        ]
        self.port_map = {
            'region-us-west': 8081,
            'region-us-east': 8082,
            'region-eu-west': 8083,
            'region-ap-south': 8084
        }

    def _detect_current_version(self):
        """Detect what version is currently deployed"""
        try:
            response = requests.get('http://localhost:8081/', timeout=5)
            data = response.json()
            current = data.get('version', 'v1')
            print(f"{Colors.BLUE}Detected current version: {current}{Colors.END}")
            return current
        except Exception as e:
            print(f"{Colors.YELLOW}Could not detect current version, assuming v1{Colors.END}")
            return 'v1'

    def health_check(self, region, retries=3):
        """Check health with retries"""
        port = self.port_map[region]

        for attempt in range(retries):
            try:
                response = requests.get(f'http://localhost:{port}/health', timeout=5)
                data = response.json()

                if response.status_code == 200 and data['status'] == 'healthy':
                    print(
                        f"    {Colors.GREEN}✓ Attempt {attempt + 1}: Healthy - version={data.get('version')}{Colors.END}")
                    return True
                else:
                    print(f"    {Colors.RED}✗ Attempt {attempt + 1}: Unhealthy - {data}{Colors.END}")
            except Exception as e:
                print(f"    {Colors.RED}✗ Attempt {attempt + 1}: Error - {e}{Colors.END}")

            time.sleep(2)

        return False

    def deploy_region(self, region):
        """Deploy to one region"""
        print(f"\n{Colors.BLUE}{'=' * 50}")
        print(f"Deploying {self.version} to {region}")
        print(f"{'=' * 50}{Colors.END}")

        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # CRITICAL: Set env vars AND export them for subprocess
        env = os.environ.copy()
        env['VERSION'] = self.version
        env['FAILURE_RATE'] = str(self.failure_rate)

        try:
            print(f"  → Stopping and removing old container...")
            subprocess.run(
                ['docker', 'compose', 'rm', '-sf', region],
                env=env,
                cwd=project_dir,
                capture_output=True
            )

            print(f"  → Starting container with VERSION={self.version}...")
            subprocess.run(
                ['docker', 'compose', 'up', '-d', '--no-deps', '--force-recreate', region],
                env=env,
                cwd=project_dir,
                check=True,
                capture_output=True,
                text=True
            )

            print(f"  → Waiting 8 seconds for service to start...")
            time.sleep(8)

            # Verify version
            port = self.port_map[region]
            try:
                resp = requests.get(f'http://localhost:{port}/', timeout=5)
                actual_version = resp.json().get('version')
                print(f"  → Verified running version: {actual_version}")

                if actual_version != self.version:
                    print(
                        f"  {Colors.RED}✗ Version mismatch! Expected {self.version}, got {actual_version}{Colors.END}")
                    return False

            except Exception as e:
                print(f"  {Colors.YELLOW}⚠ Could not verify version: {e}{Colors.END}")

            return True
        except subprocess.CalledProcessError as e:
            print(f"  {Colors.RED}✗ Deploy failed{Colors.END}")
            if e.stderr:
                print(f"  Error: {e.stderr}")
            return False

    def rollback_all(self):
        """Rollback all deployed regions to previous version"""
        print(f"\n{Colors.RED}{Colors.BOLD}{'=' * 50}")
        print(f"🔄 INITIATING AUTOMATIC ROLLBACK")
        print(f"{'=' * 50}{Colors.END}")

        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        env = os.environ.copy()
        env['VERSION'] = self.current_version
        env['FAILURE_RATE'] = '0.0'

        for region in self.deployed_regions:
            print(f"\n{Colors.YELLOW}Rolling back {region} to {self.current_version}...{Colors.END}")
            subprocess.run(
                ['docker', 'compose', 'up', '-d', '--no-deps', '--force-recreate', region],
                env=env,
                cwd=project_dir,
                capture_output=True
            )
            time.sleep(5)
            print(f"  {Colors.GREEN}✓ {region} rolled back{Colors.END}")

    def deploy(self):
        """Main deployment with rollback"""
        print(f"\n{Colors.BOLD}Starting deployment of {self.version}{Colors.END}")
        print(f"Failure rate: {self.failure_rate}")

        for i, region in enumerate(self.regions):
            # Deploy
            if not self.deploy_region(region):
                print(f"\n{Colors.RED} Deployment failed!{Colors.END}")
                self.rollback_all()
                return False

            self.deployed_regions.append(region)

            # Health check
            print(f"\n{Colors.BOLD}Health checking {region}...{Colors.END}")
            if not self.health_check(region):
                print(f"\n{Colors.RED} Health check failed!{Colors.END}")
                self.rollback_all()
                return False

            # Canary: first region gets extra monitoring
            if i == 0:
                print(f"\n{Colors.YELLOW}🐤 CANARY DEPLOYMENT{Colors.END}")
                print(f"  First region deployed - monitoring for 10 seconds...")
                for check in range(5):
                    time.sleep(2)
                    if not self.health_check(region, retries=1):
                        print(f"\n{Colors.RED} Canary monitoring failed!{Colors.END}")
                        self.rollback_all()
                        return False
                print(f"{Colors.GREEN}✓ Canary validation successful!{Colors.END}")

            print(f"\n{Colors.GREEN}✓ {region} deployed successfully{Colors.END}")

        print(f"\n{Colors.BOLD}{Colors.GREEN}✅ Deployment complete!{Colors.END}")
        return True


def main():
    if len(sys.argv) < 2:
        print(f"{Colors.RED}Usage: python deploy-with-rollback.py <version> [failure_rate]{Colors.END}")
        print(f"\nExamples:")
        print(f"  python deploy-with-rollback.py v2")
        print(f"  python deploy-with-rollback.py v3 0.8")
        sys.exit(1)

    version = sys.argv[1]
    failure_rate = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0

    deployer = Deployer(version, failure_rate)
    success = deployer.deploy()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
