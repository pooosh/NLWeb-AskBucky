#!/usr/bin/env python3
import subprocess
import sys
import os
import time
import json
from pathlib import Path
import analytics

class RobustMenuLoader:
    def __init__(self, date="2025-08-05"):
        self.date = date
        self.site_name = f"menus_{date}"
        self.data_dir = Path("../../data/jsonld")
        self.successful_files = []
        self.failed_files = []
        self.total_files = 0
        
    def find_todays_files(self):
        """Find all JSON-LD files for today"""
        files = []
        for file_path in self.data_dir.glob(f"*{self.date}.jsonld"):
            files.append(str(file_path))
        return sorted(files)
    
    def load_single_file(self, file_path, retries=3):
        """Load a single file with retry logic"""
        for attempt in range(retries):
            try:
                print(f"  Loading {os.path.basename(file_path)} (attempt {attempt + 1}/{retries})...")
                
                # Use --force-recompute to ensure fresh embeddings
                result = subprocess.run([
                    'python', '-m', 'data_loading.db_load', 
                    file_path, self.site_name, '--force-recompute'
                ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
                
                if result.returncode == 0:
                    print(f"  ✓ Successfully loaded {os.path.basename(file_path)}")
                    return True
                else:
                    print(f"  ✗ Failed to load {os.path.basename(file_path)}: {result.stderr}")
                    if attempt < retries - 1:
                        print(f"  Retrying in 5 seconds...")
                        time.sleep(5)
                    
            except subprocess.TimeoutExpired:
                print(f"  ⏰ Timeout loading {os.path.basename(file_path)}")
                if attempt < retries - 1:
                    print(f"  Retrying in 10 seconds...")
                    time.sleep(10)
            except Exception as e:
                print(f"  💥 Error loading {os.path.basename(file_path)}: {e}")
                if attempt < retries - 1:
                    print(f"  Retrying in 5 seconds...")
                    time.sleep(5)
        
        return False
    
    def load_all_files(self):
        """Load all today's files with progress tracking"""
        start_time = time.time()
        files = self.find_todays_files()
        self.total_files = len(files)
        
        print(f"🎯 Found {self.total_files} files for {self.date}")
        print(f"📁 Site name: {self.site_name}")
        print(f"🚀 Starting batch load...\n")
        
        for i, file_path in enumerate(files, 1):
            print(f"[{i}/{self.total_files}] Processing {os.path.basename(file_path)}")
            
            if self.load_single_file(file_path):
                self.successful_files.append(file_path)
            else:
                self.failed_files.append(file_path)
            
            # Progress update
            success_rate = (len(self.successful_files) / i) * 100
            print(f"📊 Progress: {i}/{self.total_files} ({success_rate:.1f}% success rate)")
            print()
            
            # Small delay to avoid overwhelming the system
            time.sleep(1)
        
        # Log job completion
        duration_ms = int((time.time() - start_time) * 1000)
        records_processed = len(self.successful_files)
        
        if len(self.failed_files) == 0:
            status = "success"
        elif len(self.successful_files) > 0:
            status = "partial"
        else:
            status = "failed"
        
        # TEMPORARILY DISABLED: analytics.log_daily_job_status(
        #     job_name="data_load",
        #     status=status,
        #     duration_ms=duration_ms,
        #     records_processed=records_processed
        # )
    
    def generate_report(self):
        """Generate a summary report"""
        print("\n" + "="*60)
        print("📋 LOADING REPORT")
        print("="*60)
        print(f"📅 Date: {self.date}")
        print(f"🏢 Site: {self.site_name}")
        print(f"✅ Successful: {len(self.successful_files)}/{self.total_files}")
        print(f"❌ Failed: {len(self.failed_files)}/{self.total_files}")
        print(f"📈 Success Rate: {(len(self.successful_files)/self.total_files)*100:.1f}%")
        
        if self.failed_files:
            print(f"\n❌ Failed Files:")
            for file_path in self.failed_files:
                print(f"  - {os.path.basename(file_path)}")
        
        if self.successful_files:
            print(f"\n✅ Successfully Loaded:")
            for file_path in self.successful_files:
                print(f"  - {os.path.basename(file_path)}")
        
        print("="*60)
    
    def save_state(self):
        """Save loading state for potential resume"""
        state = {
            'date': self.date,
            'site_name': self.site_name,
            'successful_files': self.successful_files,
            'failed_files': self.failed_files,
            'total_files': self.total_files
        }
        
        with open('loading_state.json', 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self):
        """Load previous state for resume"""
        if os.path.exists('loading_state.json'):
            with open('loading_state.json', 'r') as f:
                state = json.load(f)
            
            if state['date'] == self.date:
                self.successful_files = state['successful_files']
                self.failed_files = state['failed_files']
                self.total_files = state['total_files']
                return True
        return False

def main():
    print("🚀 Robust Menu Loader for Today's Menus")
    print("="*50)
    
    loader = RobustMenuLoader()
    
    # Check if we can resume from previous state
    if loader.load_state():
        print(f"📂 Found previous loading state for {loader.date}")
        print(f"✅ Already loaded: {len(loader.successful_files)} files")
        print(f"❌ Previously failed: {len(loader.failed_files)} files")
        
        resume = input("🔄 Resume from previous state? (y/n): ").lower().strip()
        if resume != 'y':
            loader.successful_files = []
            loader.failed_files = []
    
    try:
        loader.load_all_files()
        loader.generate_report()
        loader.save_state()
        
        if loader.failed_files:
            print(f"\n⚠️  {len(loader.failed_files)} files failed to load.")
            print("💡 You can run this script again to retry failed files.")
        else:
            print(f"\n🎉 All {loader.total_files} files loaded successfully!")
            
    except KeyboardInterrupt:
        print(f"\n⏸️  Loading interrupted by user.")
        loader.save_state()
        print(f"💾 State saved. Run again to resume.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        loader.save_state()
        print(f"💾 State saved. Run again to resume.")
        sys.exit(1)

if __name__ == "__main__":
    main() 