#!/usr/bin/env python3
"""
ApexRML Setup Script
Automatically configures Git and clones the repository
Run this: python setup.py
"""

import subprocess
import os
import sys

def run_command(cmd, description=""):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✅ {description}")
            if result.stdout:
                print(f"   {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description}")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    print("=" * 60)
    print("🚀 ApexRML Setup Script")
    print("=" * 60)
    print()
    
    # Step 1: Verify Git Installation
    print("📋 Step 1: Verifying Git Installation...")
    if run_command("git --version", "Git is installed"):
        print()
    else:
        print("❌ Git is not installed!")
        print("   Please install Git from: https://git-scm.com/download/win")
        sys.exit(1)
    
    # Step 2: Configure Git
    print("📋 Step 2: Configuring Git...")
    
    # Get user info
    print()
    user_name = input("Enter your name (for Git commits): ").strip()
    if not user_name:
        user_name = "ApexRML Developer"
    
    user_email = input("Enter your email (for Git commits): ").strip()
    if not user_email:
        user_email = "developer@apexrml.co.uk"
    
    print()
    run_command(f'git config --global user.name "{user_name}"', f"Configured Git user: {user_name}")
    run_command(f'git config --global user.email "{user_email}"', f"Configured Git email: {user_email}")
    print()
    
    # Step 3: Get GitHub URL
    print("📋 Step 3: Cloning ApexRML Repository...")
    print()
    
    github_url = input("Enter your GitHub repository URL\n(e.g., https://github.com/YOUR-USERNAME/ApexRML.git): ").strip()
    
    if not github_url:
        print("❌ No GitHub URL provided. Exiting.")
        sys.exit(1)
    
    print()
    
    # Step 4: Create ApexRML folder and clone
    apexrml_path = os.path.expanduser("~/ApexRML")
    
    # Create directory
    try:
        os.makedirs(apexrml_path, exist_ok=True)
        print(f"✅ Created folder: {apexrml_path}")
    except Exception as e:
        print(f"❌ Failed to create folder: {str(e)}")
        sys.exit(1)
    
    print()
    
    # Clone repository
    print(f"📥 Cloning repository from: {github_url}")
    print("   (This may take a minute...)")
    print()
    
    if run_command(f'cd "{apexrml_path}" && git clone "{github_url}" .', "Repository cloned successfully"):
        print()
        print("=" * 60)
        print("✅ Setup Complete!")
        print("=" * 60)
        print()
        print(f"📁 Your ApexRML project is ready at: {apexrml_path}")
        print()
        print("🚀 Next Steps:")
        print("   1. Download all 13 ApexRML files from Claude outputs")
        print("   2. Copy them to: " + apexrml_path)
        print("   3. Organize files in correct folder structure")
        print("   4. Run: git add .")
        print("   5. Run: git commit -m 'Initial ApexRML commit'")
        print("   6. Run: git push origin main")
        print("   7. Deploy to Render.com")
        print()
        print("📖 See RENDER_DEPLOYMENT_GUIDE.md for detailed instructions")
        print()
    else:
        print("❌ Failed to clone repository")
        print("   Check that your GitHub URL is correct and you have internet access")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        sys.exit(1)
