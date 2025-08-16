
#!/usr/bin/env python3
"""
Migration script to move existing tests to the new file-based system
"""

import os
import json
import shutil
from datetime import datetime
from data_manager import get_practice_tests, get_full_mock_tests
from test_data_manager import test_manager

def backup_old_data():
    """Create backup of old test data"""
    backup_dir = f"data/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    # Backup existing files
    files_to_backup = [
        'data/practice_tests.json',
        'data/full_mock_tests.json'
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            filename = os.path.basename(file_path)
            shutil.copy2(file_path, os.path.join(backup_dir, filename))
            print(f"Backed up {file_path}")
    
    return backup_dir

def migrate_tests():
    """Migrate existing tests to new file-based system"""
    print("Starting test migration...")
    
    # Create backup
    backup_dir = backup_old_data()
    print(f"Backup created at: {backup_dir}")
    
    migrated_count = 0
    
    try:
        # Migrate practice tests
        practice_tests = get_practice_tests()
        print(f"Found {len(practice_tests)} practice tests to migrate")
        
        for old_test in practice_tests:
            try:
                # Create new test structure
                new_test_id = test_manager.create_test(
                    title=old_test.get('title', f'Migrated Test {old_test.get("id", "Unknown")}'),
                    section=old_test.get('section', 'Reading'),
                    duration=old_test.get('duration_minutes', 60),
                    description=old_test.get('description', ''),
                    is_mock=False,
                    is_premium=old_test.get('is_premium', False)
                )
                
                if new_test_id:
                    # Migrate content if exists
                    if 'content' in old_test and 'sections' in old_test['content']:
                        for section_name, section_data in old_test['content']['sections'].items():
                            test_manager.update_test_section(new_test_id, section_name, section_data, False)
                    
                    print(f"Migrated practice test: {old_test.get('title')} -> ID {new_test_id}")
                    migrated_count += 1
                
            except Exception as e:
                print(f"Error migrating practice test {old_test.get('id')}: {e}")
        
        # Migrate mock tests
        mock_tests = get_full_mock_tests()
        print(f"Found {len(mock_tests)} mock tests to migrate")
        
        for old_test in mock_tests:
            try:
                # Create new test structure
                new_test_id = test_manager.create_test(
                    title=old_test.get('title', f'Migrated Mock Test {old_test.get("id", "Unknown")}'),
                    section=old_test.get('section', 'All Sections'),
                    duration=old_test.get('duration_minutes', 180),
                    description=old_test.get('description', ''),
                    is_mock=True,
                    is_premium=old_test.get('is_premium', False)
                )
                
                if new_test_id:
                    # Migrate content if exists
                    if 'content' in old_test and 'sections' in old_test['content']:
                        for section_name, section_data in old_test['content']['sections'].items():
                            test_manager.update_test_section(new_test_id, section_name, section_data, True)
                    
                    print(f"Migrated mock test: {old_test.get('title')} -> ID {new_test_id}")
                    migrated_count += 1
                
            except Exception as e:
                print(f"Error migrating mock test {old_test.get('id')}: {e}")
        
        print(f"Migration completed! Migrated {migrated_count} tests")
        print(f"Old data backed up to: {backup_dir}")
        
        # Show statistics
        stats = test_manager.get_test_statistics()
        print("\nNew system statistics:")
        print(f"Practice tests: {stats['total_practice_tests']}")
        print(f"Mock tests: {stats['total_mock_tests']}")
        print(f"Total tests: {stats['total_practice_tests'] + stats['total_mock_tests']}")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        print(f"Old data is safely backed up in: {backup_dir}")

if __name__ == "__main__":
    migrate_tests()
