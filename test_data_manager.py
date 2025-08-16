import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any

# Base directories
DATA_DIR = 'data'
TESTS_DIR = os.path.join(DATA_DIR, 'tests')
MOCK_TESTS_DIR = os.path.join(DATA_DIR, 'mock_tests')

# Ensure directories exist
os.makedirs(TESTS_DIR, exist_ok=True)
os.makedirs(MOCK_TESTS_DIR, exist_ok=True)

class TestDataManager:
    """Enhanced test data manager with separate files for each test and section"""

    def __init__(self):
        self.base_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.tests_dir = os.path.join(self.base_dir, 'tests')
        self.mock_tests_dir = os.path.join(self.base_dir, 'mock_tests')

        # Ensure directories exist
        os.makedirs(self.tests_dir, exist_ok=True)
        os.makedirs(self.mock_tests_dir, exist_ok=True)

        # Create mock test directories for comprehensive tests
        for test_id in [100, 101, 102]:
            mock_test_dir = os.path.join(self.mock_tests_dir, f'test_{test_id}')
            os.makedirs(mock_test_dir, exist_ok=True)

        self.sections = ['reading', 'listening', 'writing', 'speaking']

    def _get_test_dir(self, test_id: int, is_mock: bool = False) -> str:
        """Get the directory path for a specific test"""
        base_dir = MOCK_TESTS_DIR if is_mock else TESTS_DIR
        return os.path.join(base_dir, f'test_{test_id}')

    def _get_section_file(self, test_id: int, section: str, is_mock: bool = False) -> str:
        """Get the file path for a specific test section"""
        test_dir = self._get_test_dir(test_id, is_mock)
        return os.path.join(test_dir, f'{section}.json')

    def _get_metadata_file(self, test_id: int, is_mock: bool = False) -> str:
        """Get the metadata file path for a test"""
        test_dir = self._get_test_dir(test_id, is_mock)
        return os.path.join(test_dir, 'metadata.json')

    def _load_json_file(self, filepath: str, default: Any = None) -> Any:
        """Load JSON data from file"""
        if default is None:
            default = {}

        if not os.path.exists(filepath):
            return default

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return default

    def _save_json_file(self, filepath: str, data: Any) -> bool:
        """Save JSON data to file"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving file {filepath}: {e}")
            return False

    def get_next_test_id(self, is_mock: bool = False) -> int:
        """Get the next available test ID"""
        base_dir = MOCK_TESTS_DIR if is_mock else TESTS_DIR
        existing_ids = []

        if os.path.exists(base_dir):
            for item in os.listdir(base_dir):
                if item.startswith('test_') and os.path.isdir(os.path.join(base_dir, item)):
                    try:
                        test_id = int(item.replace('test_', ''))
                        existing_ids.append(test_id)
                    except ValueError:
                        continue

        return max(existing_ids, default=0) + 1

    def create_test(self, title: str, section: str, duration: int, description: str,
                   is_mock: bool = False, is_premium: bool = False) -> Optional[int]:
        """Create a new test with separate files for each section"""
        test_id = self.get_next_test_id(is_mock)
        test_dir = self._get_test_dir(test_id, is_mock)

        try:
            # Create test directory
            os.makedirs(test_dir, exist_ok=True)

            # Create metadata
            metadata = {
                'id': test_id,
                'title': title,
                'section': section,
                'duration_minutes': duration,
                'description': description,
                'is_mock_test': is_mock,
                'is_premium': is_premium,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            # Save metadata
            metadata_file = self._get_metadata_file(test_id, is_mock)
            if not self._save_json_file(metadata_file, metadata):
                return None

            # Create empty section files
            for sec in self.sections:
                section_file = self._get_section_file(test_id, sec, is_mock)
                default_content = self._get_default_section_content(sec)
                self._save_json_file(section_file, default_content)

            return test_id

        except Exception as e:
            print(f"Error creating test: {e}")
            return None

    def _get_default_section_content(self, section: str) -> Dict:
        """Get default content structure for a section"""
        if section == 'reading':
            return {
                'duration_minutes': 45,
                'passages': [],
                'questions': []
            }
        elif section == 'listening':
            return {
                'duration_minutes': 30,
                'audio_files': [],
                'questions': []
            }
        elif section == 'writing':
            return {
                'duration_minutes': 45,
                'scenario': {},
                'questions': []
            }
        elif section == 'speaking':
            return {
                'duration_minutes': 20,
                'role_plays': [],
                'questions': []
            }
        else:
            return {}

    def get_test_metadata(self, test_id: int, is_mock: bool = False) -> Optional[Dict]:
        """Get test metadata"""
        metadata_file = self._get_metadata_file(test_id, is_mock)
        return self._load_json_file(metadata_file)

    def get_test_section(self, test_id: int, section: str, is_mock: bool = False) -> Dict:
        """Get content for a specific test section"""
        section_file = self._get_section_file(test_id, section, is_mock)
        return self._load_json_file(section_file, self._get_default_section_content(section))

    def update_test_metadata(self, test_id: int, metadata: Dict, is_mock: bool = False) -> bool:
        """Update test metadata"""
        metadata['updated_at'] = datetime.now().isoformat()
        metadata_file = self._get_metadata_file(test_id, is_mock)
        return self._save_json_file(metadata_file, metadata)

    def update_test_section(self, test_id: int, section: str, content: Dict, is_mock: bool = False) -> bool:
        """Update content for a specific test section"""
        section_file = self._get_section_file(test_id, section, is_mock)
        return self._save_json_file(section_file, content)

    def get_complete_test(self, test_id: int, is_mock: bool = False) -> Optional[Dict]:
        """Get complete test data including all sections"""
        metadata = self.get_test_metadata(test_id, is_mock)
        if not metadata:
            return None

        # Load all sections
        sections = {}
        for section in self.sections:
            sections[section] = self.get_test_section(test_id, section, is_mock)

        # Combine metadata and sections
        test_data = metadata.copy()
        test_data['content'] = {'sections': sections}
        test_data['test_type'] = 'mock' if is_mock else 'practice'

        return test_data

    def get_all_tests(self, is_mock: bool = False) -> List[Dict]:
        """Get all tests of specified type"""
        tests = []
        base_dir = MOCK_TESTS_DIR if is_mock else TESTS_DIR

        if not os.path.exists(base_dir):
            return tests

        for item in os.listdir(base_dir):
            if item.startswith('test_') and os.path.isdir(os.path.join(base_dir, item)):
                try:
                    test_id = int(item.replace('test_', ''))
                    test_data = self.get_complete_test(test_id, is_mock)
                    if test_data:
                        tests.append(test_data)
                except ValueError:
                    continue

        # Sort by ID
        tests.sort(key=lambda x: x.get('id', 0))
        return tests

    def delete_test(self, test_id: int, is_mock: bool = False) -> bool:
        """Delete a test and all its files"""
        test_dir = self._get_test_dir(test_id, is_mock)

        try:
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
                return True
            return False
        except Exception as e:
            print(f"Error deleting test {test_id}: {e}")
            return False

    def duplicate_test(self, source_test_id: int, new_title: str,
                      source_is_mock: bool = False, target_is_mock: bool = False) -> Optional[int]:
        """Duplicate a test to create a new one"""
        source_test = self.get_complete_test(source_test_id, source_is_mock)
        if not source_test:
            return None

        # Create new test
        new_test_id = self.create_test(
            title=new_title,
            section=source_test['section'],
            duration=source_test['duration_minutes'],
            description=source_test['description'],
            is_mock=target_is_mock,
            is_premium=source_test.get('is_premium', False)
        )

        if not new_test_id:
            return None

        # Copy all section content
        for section in self.sections:
            section_content = source_test['content']['sections'].get(section, {})
            self.update_test_section(new_test_id, section, section_content, target_is_mock)

        return new_test_id

    def get_test_statistics(self) -> Dict:
        """Get statistics about tests in the system"""
        practice_tests = self.get_all_tests(is_mock=False)
        mock_tests = self.get_all_tests(is_mock=True)

        stats = {
            'total_practice_tests': len(practice_tests),
            'total_mock_tests': len(mock_tests),
            'practice_by_section': {},
            'mock_by_section': {}
        }

        for test in practice_tests:
            section = test.get('section', 'Unknown')
            stats['practice_by_section'][section] = stats['practice_by_section'].get(section, 0) + 1

        for test in mock_tests:
            section = test.get('section', 'Unknown')
            stats['mock_by_section'][section] = stats['mock_by_section'].get(section, 0) + 1

        return stats

# Global instance
test_manager = TestDataManager()