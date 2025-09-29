import pandas as pd
from typing import Dict, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InputParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.courses = {}
        self.teachers = {}
        self.rooms = {}
        self.timeslots = {}
        self.groups = {}

    def parse_excel(self, excel_file=None) -> Tuple[Dict, Dict, Dict, Dict, Dict]:
        """Parse the Excel file and return structured data"""
        try:
            # Use provided ExcelFile or open a new one
            if excel_file is None:
                excel_file = pd.ExcelFile(self.file_path)

            # Parse courses
            if 'Courses' in excel_file.sheet_names:
                courses_df = pd.read_excel(excel_file, sheet_name='Courses')
                self._parse_courses(courses_df)

            # Parse teachers
            if 'Teachers' in excel_file.sheet_names:
                teachers_df = pd.read_excel(excel_file, sheet_name='Teachers')
                self._parse_teachers(teachers_df)

            # Parse rooms
            if 'Rooms' in excel_file.sheet_names:
                rooms_df = pd.read_excel(excel_file, sheet_name='Rooms')
                self._parse_rooms(rooms_df)

            # Parse timeslots
            if 'Timeslots' in excel_file.sheet_names:
                timeslots_df = pd.read_excel(excel_file, sheet_name='Timeslots')
                self._parse_timeslots(timeslots_df)

            # Parse groups
            if 'Groups' in excel_file.sheet_names:
                groups_df = pd.read_excel(excel_file, sheet_name='Groups')
                self._parse_groups(groups_df)

            logger.info("Successfully parsed Excel file")
            return self.courses, self.teachers, self.rooms, self.timeslots, self.groups

        except Exception as e:
            logger.error(f"Error parsing Excel file: {str(e)}")
            raise e

    def _parse_courses(self, df: pd.DataFrame):
        """Parse courses sheet"""
        required_columns = ['CourseID', 'CourseName', 'Type', 'Semester', 'Duration']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Courses sheet: {missing}")
        
        for _, row in df.iterrows():
            course_id = str(row['CourseID']).strip()
            self.courses[course_id] = {
                'course_name': str(row['CourseName']).strip(),
                'type': str(row['Type']).strip().upper(),
                'semester': str(row['Semester']).strip(),
                'duration': int(row['Duration']) if pd.notna(row['Duration']) else 1
            }
        logger.info(f"Parsed {len(self.courses)} courses")

    def _parse_teachers(self, df: pd.DataFrame):
        """Parse teachers sheet"""
        required_columns = ['TeacherID', 'TeacherName', 'CoursesHandled']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Teachers sheet: {missing}")
        
        for _, row in df.iterrows():
            teacher_id = str(row['TeacherID']).strip()

            # Parse courses handled - can be comma-separated
            courses_handled = []
            if pd.notna(row['CoursesHandled']):
                courses_str = str(row['CoursesHandled']).strip()
                courses_handled = [c.strip() for c in courses_str.split(',') if c.strip()]

            # Parse availability constraints
            availability = []
            if pd.notna(row.get('Availability', '')):
                avail_str = str(row['Availability']).strip()
                if avail_str:
                    availability = [a.strip() for a in avail_str.split(',') if a.strip()]

            self.teachers[teacher_id] = {
                'teacher_name': str(row['TeacherName']).strip(),
                'courses_handled': courses_handled,
                'availability': availability
            }
        logger.info(f"Parsed {len(self.teachers)} teachers")

    def _parse_rooms(self, df: pd.DataFrame):
        """Parse rooms sheet"""
        required_columns = ['RoomID', 'Capacity', 'Type']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Rooms sheet: {missing}")
        
        for _, row in df.iterrows():
            room_id = str(row['RoomID']).strip()
            self.rooms[room_id] = {
                'capacity': int(row['Capacity']) if pd.notna(row['Capacity']) else 50,
                'type': str(row['Type']).strip().lower(),
            }
        logger.info(f"Parsed {len(self.rooms)} rooms")

    def _parse_timeslots(self, df: pd.DataFrame):
        """Parse timeslots sheet"""
        required_columns = ['SlotID', 'Day', 'Time']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Timeslots sheet: {missing}")
        
        for _, row in df.iterrows():
            slot_id = str(row['SlotID']).strip()
            self.timeslots[slot_id] = {
                'day': str(row['Day']).strip(),
                'time': str(row['Time']).strip(),
                'slot_index': len(self.timeslots)  # For ordering
            }
        logger.info(f"Parsed {len(self.timeslots)} timeslots")

    def _parse_groups(self, df: pd.DataFrame):
        """Parse groups sheet"""
        required_columns = ['GroupID', 'Semester', 'Courses']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Groups sheet: {missing}")
        
        for _, row in df.iterrows():
            group_id = str(row['GroupID']).strip()

            # Parse courses for this group
            courses = []
            if pd.notna(row['Courses']):
                courses_str = str(row['Courses']).strip()
                courses = [c.strip() for c in courses_str.split(',') if c.strip()]

            self.groups[group_id] = {
                'semester': str(row['Semester']).strip(),
                'courses': courses
            }
        logger.info(f"Parsed {len(self.groups)} groups")

    def validate_data(self) -> List[str]:
        """Validate parsed data for consistency"""
        errors = []

        # Check if teacher's courses exist
        for teacher_id, teacher_data in self.teachers.items():
            for course_id in teacher_data['courses_handled']:
                if course_id not in self.courses:
                    errors.append(f"Teacher {teacher_id} assigned to non-existent course {course_id}")

        # Check if group's courses exist
        for group_id, group_data in self.groups.items():
            for course_id in group_data['courses']:
                if course_id not in self.courses:
                    errors.append(f"Group {group_id} assigned to non-existent course {course_id}")

        # Check if all courses have teachers
        for course_id in self.courses:
            has_teacher = any(course_id in teacher['courses_handled'] 
                            for teacher in self.teachers.values())
            if not has_teacher:
                errors.append(f"Course {course_id} has no assigned teacher")

        if errors:
            logger.warning(f"Validation found {len(errors)} issues")
        else:
            logger.info("Data validation successful")

        return errors

def create_sample_data():
    """Create sample Excel file for testing"""
    import pandas as pd

    # Sample courses data
    courses_data = {
        'CourseID': ['DDBMS', 'AWS-CCS', 'AI-ML', 'SOFTWARE-TESTING', 'PROJECT'],
        'CourseName': ['Distributed Database Management Systems', 'Cloud Computing with AWS', 
                      'Artificial Intelligence & Machine Learning', 'Software Testing', 'Major Project'],
        'Type': ['TH', 'TH', 'TH', 'LAB', 'PROJECT'],
        'Semester': ['VII-A', 'VII-A', 'VII-B', 'VII-A', 'VII-B'],
        'Duration': [1, 1, 1, 2, 2]
    }

    # Sample teachers data
    teachers_data = {
        'TeacherID': ['T001', 'T002', 'T003', 'T004', 'T005'],
        'TeacherName': ['Dr. Smith', 'Prof. Johnson', 'Dr. Brown', 'Ms. Davis', 'Mr. Wilson'],
        'CoursesHandled': ['DDBMS', 'AWS-CCS', 'AI-ML', 'SOFTWARE-TESTING', 'PROJECT'],
        'Availability': ['', '', 'Monday-Morning', '', '']
    }

    # Sample rooms data
    rooms_data = {
        'RoomID': ['R101', 'R102', 'LAB1', 'LAB2', 'PROJ-ROOM'],
        'Capacity': [60, 60, 30, 30, 25],
        'Type': ['classroom', 'classroom', 'lab', 'lab', 'project room']
    }

    # Sample timeslots data
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    times = ['09:30-10:30', '10:30-11:30', '11:30-12:30', '14:00-15:00', '15:00-16:00', '16:00-17:00']

    timeslots_data = {
        'SlotID': [],
        'Day': [],
        'Time': []
    }

    slot_id = 1
    for day in days:
        for time in times:
            timeslots_data['SlotID'].append(f'S{slot_id:03d}')
            timeslots_data['Day'].append(day)
            timeslots_data['Time'].append(time)
            slot_id += 1

    # Sample groups data
    groups_data = {
        'GroupID': ['AI-VII-A', 'AI-VII-B'],
        'Semester': ['VII-A', 'VII-B'],
        'Courses': ['DDBMS,AWS-CCS,SOFTWARE-TESTING', 'AI-ML,PROJECT']
    }

    # Create Excel file
    with pd.ExcelWriter('sample_input.xlsx', engine='openpyxl') as writer:
        pd.DataFrame(courses_data).to_excel(writer, sheet_name='Courses', index=False)
        pd.DataFrame(teachers_data).to_excel(writer, sheet_name='Teachers', index=False)
        pd.DataFrame(rooms_data).to_excel(writer, sheet_name='Rooms', index=False)
        pd.DataFrame(timeslots_data).to_excel(writer, sheet_name='Timeslots', index=False)
        pd.DataFrame(groups_data).to_excel(writer, sheet_name='Groups', index=False)

    logger.info("Sample Excel file 'sample_input.xlsx' created successfully")import pandas as pd
from typing import Dict, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InputParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.courses = {}
        self.teachers = {}
        self.rooms = {}
        self.timeslots = {}
        self.groups = {}

    def parse_excel(self, excel_file=None) -> Tuple[Dict, Dict, Dict, Dict, Dict]:
        """Parse the Excel file and return structured data"""
        try:
            # Use provided ExcelFile or open a new one
            if excel_file is None:
                excel_file = pd.ExcelFile(self.file_path)

            # Parse courses
            if 'Courses' in excel_file.sheet_names:
                courses_df = pd.read_excel(excel_file, sheet_name='Courses')
                self._parse_courses(courses_df)

            # Parse teachers
            if 'Teachers' in excel_file.sheet_names:
                teachers_df = pd.read_excel(excel_file, sheet_name='Teachers')
                self._parse_teachers(teachers_df)

            # Parse rooms
            if 'Rooms' in excel_file.sheet_names:
                rooms_df = pd.read_excel(excel_file, sheet_name='Rooms')
                self._parse_rooms(rooms_df)

            # Parse timeslots
            if 'Timeslots' in excel_file.sheet_names:
                timeslots_df = pd.read_excel(excel_file, sheet_name='Timeslots')
                self._parse_timeslots(timeslots_df)

            # Parse groups
            if 'Groups' in excel_file.sheet_names:
                groups_df = pd.read_excel(excel_file, sheet_name='Groups')
                self._parse_groups(groups_df)

            logger.info("Successfully parsed Excel file")
            return self.courses, self.teachers, self.rooms, self.timeslots, self.groups

        except Exception as e:
            logger.error(f"Error parsing Excel file: {str(e)}")
            raise e

    def _parse_courses(self, df: pd.DataFrame):
        """Parse courses sheet"""
        required_columns = ['CourseID', 'CourseName', 'Type', 'Semester', 'Duration']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Courses sheet: {missing}")
        
        for _, row in df.iterrows():
            course_id = str(row['CourseID']).strip()
            self.courses[course_id] = {
                'course_name': str(row['CourseName']).strip(),
                'type': str(row['Type']).strip().upper(),
                'semester': str(row['Semester']).strip(),
                'duration': int(row['Duration']) if pd.notna(row['Duration']) else 1
            }
        logger.info(f"Parsed {len(self.courses)} courses")

    def _parse_teachers(self, df: pd.DataFrame):
        """Parse teachers sheet"""
        required_columns = ['TeacherID', 'TeacherName', 'CoursesHandled']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Teachers sheet: {missing}")
        
        for _, row in df.iterrows():
            teacher_id = str(row['TeacherID']).strip()

            # Parse courses handled - can be comma-separated
            courses_handled = []
            if pd.notna(row['CoursesHandled']):
                courses_str = str(row['CoursesHandled']).strip()
                courses_handled = [c.strip() for c in courses_str.split(',') if c.strip()]

            # Parse availability constraints
            availability = []
            if pd.notna(row.get('Availability', '')):
                avail_str = str(row['Availability']).strip()
                if avail_str:
                    availability = [a.strip() for a in avail_str.split(',') if a.strip()]

            self.teachers[teacher_id] = {
                'teacher_name': str(row['TeacherName']).strip(),
                'courses_handled': courses_handled,
                'availability': availability
            }
        logger.info(f"Parsed {len(self.teachers)} teachers")

    def _parse_rooms(self, df: pd.DataFrame):
        """Parse rooms sheet"""
        required_columns = ['RoomID', 'Capacity', 'Type']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Rooms sheet: {missing}")
        
        for _, row in df.iterrows():
            room_id = str(row['RoomID']).strip()
            self.rooms[room_id] = {
                'capacity': int(row['Capacity']) if pd.notna(row['Capacity']) else 50,
                'type': str(row['Type']).strip().lower(),
            }
        logger.info(f"Parsed {len(self.rooms)} rooms")

    def _parse_timeslots(self, df: pd.DataFrame):
        """Parse timeslots sheet"""
        required_columns = ['SlotID', 'Day', 'Time']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Timeslots sheet: {missing}")
        
        for _, row in df.iterrows():
            slot_id = str(row['SlotID']).strip()
            self.timeslots[slot_id] = {
                'day': str(row['Day']).strip(),
                'time': str(row['Time']).strip(),
                'slot_index': len(self.timeslots)  # For ordering
            }
        logger.info(f"Parsed {len(self.timeslots)} timeslots")

    def _parse_groups(self, df: pd.DataFrame):
        """Parse groups sheet"""
        required_columns = ['GroupID', 'Semester', 'Courses']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Groups sheet: {missing}")
        
        for _, row in df.iterrows():
            group_id = str(row['GroupID']).strip()

            # Parse courses for this group
            courses = []
            if pd.notna(row['Courses']):
                courses_str = str(row['Courses']).strip()
                courses = [c.strip() for c in courses_str.split(',') if c.strip()]

            self.groups[group_id] = {
                'semester': str(row['Semester']).strip(),
                'courses': courses
            }
        logger.info(f"Parsed {len(self.groups)} groups")

    def validate_data(self) -> List[str]:
        """Validate parsed data for consistency"""
        errors = []

        # Check if teacher's courses exist
        for teacher_id, teacher_data in self.teachers.items():
            for course_id in teacher_data['courses_handled']:
                if course_id not in self.courses:
                    errors.append(f"Teacher {teacher_id} assigned to non-existent course {course_id}")

        # Check if group's courses exist
        for group_id, group_data in self.groups.items():
            for course_id in group_data['courses']:
                if course_id not in self.courses:
                    errors.append(f"Group {group_id} assigned to non-existent course {course_id}")

        # Check if all courses have teachers
        for course_id in self.courses:
            has_teacher = any(course_id in teacher['courses_handled'] 
                            for teacher in self.teachers.values())
            if not has_teacher:
                errors.append(f"Course {course_id} has no assigned teacher")

        if errors:
            logger.warning(f"Validation found {len(errors)} issues")
        else:
            logger.info("Data validation successful")

        return errors

def create_sample_data():
    """Create sample Excel file for testing"""
    import pandas as pd

    # Sample courses data
    courses_data = {
        'CourseID': ['DDBMS', 'AWS-CCS', 'AI-ML', 'SOFTWARE-TESTING', 'PROJECT'],
        'CourseName': ['Distributed Database Management Systems', 'Cloud Computing with AWS', 
                      'Artificial Intelligence & Machine Learning', 'Software Testing', 'Major Project'],
        'Type': ['TH', 'TH', 'TH', 'LAB', 'PROJECT'],
        'Semester': ['VII-A', 'VII-A', 'VII-B', 'VII-A', 'VII-B'],
        'Duration': [1, 1, 1, 2, 2]
    }

    # Sample teachers data
    teachers_data = {
        'TeacherID': ['T001', 'T002', 'T003', 'T004', 'T005'],
        'TeacherName': ['Dr. Smith', 'Prof. Johnson', 'Dr. Brown', 'Ms. Davis', 'Mr. Wilson'],
        'CoursesHandled': ['DDBMS', 'AWS-CCS', 'AI-ML', 'SOFTWARE-TESTING', 'PROJECT'],
        'Availability': ['', '', 'Monday-Morning', '', '']
    }

    # Sample rooms data
    rooms_data = {
        'RoomID': ['R101', 'R102', 'LAB1', 'LAB2', 'PROJ-ROOM'],
        'Capacity': [60, 60, 30, 30, 25],
        'Type': ['classroom', 'classroom', 'lab', 'lab', 'project room']
    }

    # Sample timeslots data
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    times = ['09:30-10:30', '10:30-11:30', '11:30-12:30', '14:00-15:00', '15:00-16:00', '16:00-17:00']

    timeslots_data = {
        'SlotID': [],
        'Day': [],
        'Time': []
    }

    slot_id = 1
    for day in days:
        for time in times:
            timeslots_data['SlotID'].append(f'S{slot_id:03d}')
            timeslots_data['Day'].append(day)
            timeslots_data['Time'].append(time)
            slot_id += 1

    # Sample groups data
    groups_data = {
        'GroupID': ['AI-VII-A', 'AI-VII-B'],
        'Semester': ['VII-A', 'VII-B'],
        'Courses': ['DDBMS,AWS-CCS,SOFTWARE-TESTING', 'AI-ML,PROJECT']
    }

    # Create Excel file
    with pd.ExcelWriter('sample_input.xlsx', engine='openpyxl') as writer:
        pd.DataFrame(courses_data).to_excel(writer, sheet_name='Courses', index=False)
        pd.DataFrame(teachers_data).to_excel(writer, sheet_name='Teachers', index=False)
        pd.DataFrame(rooms_data).to_excel(writer, sheet_name='Rooms', index=False)
        pd.DataFrame(timeslots_data).to_excel(writer, sheet_name='Timeslots', index=False)
        pd.DataFrame(groups_data).to_excel(writer, sheet_name='Groups', index=False)

    logger.info("Sample Excel file 'sample_input.xlsx' created successfully")import pandas as pd
from typing import Dict, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InputParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.courses = {}
        self.teachers = {}
        self.rooms = {}
        self.timeslots = {}
        self.groups = {}

    def parse_excel(self, excel_file=None) -> Tuple[Dict, Dict, Dict, Dict, Dict]:
        """Parse the Excel file and return structured data"""
        try:
            # Use provided ExcelFile or open a new one
            if excel_file is None:
                excel_file = pd.ExcelFile(self.file_path)

            # Parse courses
            if 'Courses' in excel_file.sheet_names:
                courses_df = pd.read_excel(excel_file, sheet_name='Courses')
                self._parse_courses(courses_df)

            # Parse teachers
            if 'Teachers' in excel_file.sheet_names:
                teachers_df = pd.read_excel(excel_file, sheet_name='Teachers')
                self._parse_teachers(teachers_df)

            # Parse rooms
            if 'Rooms' in excel_file.sheet_names:
                rooms_df = pd.read_excel(excel_file, sheet_name='Rooms')
                self._parse_rooms(rooms_df)

            # Parse timeslots
            if 'Timeslots' in excel_file.sheet_names:
                timeslots_df = pd.read_excel(excel_file, sheet_name='Timeslots')
                self._parse_timeslots(timeslots_df)

            # Parse groups
            if 'Groups' in excel_file.sheet_names:
                groups_df = pd.read_excel(excel_file, sheet_name='Groups')
                self._parse_groups(groups_df)

            logger.info("Successfully parsed Excel file")
            return self.courses, self.teachers, self.rooms, self.timeslots, self.groups

        except Exception as e:
            logger.error(f"Error parsing Excel file: {str(e)}")
            raise e

    def _parse_courses(self, df: pd.DataFrame):
        """Parse courses sheet"""
        required_columns = ['CourseID', 'CourseName', 'Type', 'Semester', 'Duration']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Courses sheet: {missing}")
        
        for _, row in df.iterrows():
            course_id = str(row['CourseID']).strip()
            self.courses[course_id] = {
                'course_name': str(row['CourseName']).strip(),
                'type': str(row['Type']).strip().upper(),
                'semester': str(row['Semester']).strip(),
                'duration': int(row['Duration']) if pd.notna(row['Duration']) else 1
            }
        logger.info(f"Parsed {len(self.courses)} courses")

    def _parse_teachers(self, df: pd.DataFrame):
        """Parse teachers sheet"""
        required_columns = ['TeacherID', 'TeacherName', 'CoursesHandled']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Teachers sheet: {missing}")
        
        for _, row in df.iterrows():
            teacher_id = str(row['TeacherID']).strip()

            # Parse courses handled - can be comma-separated
            courses_handled = []
            if pd.notna(row['CoursesHandled']):
                courses_str = str(row['CoursesHandled']).strip()
                courses_handled = [c.strip() for c in courses_str.split(',') if c.strip()]

            # Parse availability constraints
            availability = []
            if pd.notna(row.get('Availability', '')):
                avail_str = str(row['Availability']).strip()
                if avail_str:
                    availability = [a.strip() for a in avail_str.split(',') if a.strip()]

            self.teachers[teacher_id] = {
                'teacher_name': str(row['TeacherName']).strip(),
                'courses_handled': courses_handled,
                'availability': availability
            }
        logger.info(f"Parsed {len(self.teachers)} teachers")

    def _parse_rooms(self, df: pd.DataFrame):
        """Parse rooms sheet"""
        required_columns = ['RoomID', 'Capacity', 'Type']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Rooms sheet: {missing}")
        
        for _, row in df.iterrows():
            room_id = str(row['RoomID']).strip()
            self.rooms[room_id] = {
                'capacity': int(row['Capacity']) if pd.notna(row['Capacity']) else 50,
                'type': str(row['Type']).strip().lower(),
            }
        logger.info(f"Parsed {len(self.rooms)} rooms")

    def _parse_timeslots(self, df: pd.DataFrame):
        """Parse timeslots sheet"""
        required_columns = ['SlotID', 'Day', 'Time']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Timeslots sheet: {missing}")
        
        for _, row in df.iterrows():
            slot_id = str(row['SlotID']).strip()
            self.timeslots[slot_id] = {
                'day': str(row['Day']).strip(),
                'time': str(row['Time']).strip(),
                'slot_index': len(self.timeslots)  # For ordering
            }
        logger.info(f"Parsed {len(self.timeslots)} timeslots")

    def _parse_groups(self, df: pd.DataFrame):
        """Parse groups sheet"""
        required_columns = ['GroupID', 'Semester', 'Courses']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Groups sheet: {missing}")
        
        for _, row in df.iterrows():
            group_id = str(row['GroupID']).strip()

            # Parse courses for this group
            courses = []
            if pd.notna(row['Courses']):
                courses_str = str(row['Courses']).strip()
                courses = [c.strip() for c in courses_str.split(',') if c.strip()]

            self.groups[group_id] = {
                'semester': str(row['Semester']).strip(),
                'courses': courses
            }
        logger.info(f"Parsed {len(self.groups)} groups")

    def validate_data(self) -> List[str]:
        """Validate parsed data for consistency"""
        errors = []

        # Check if teacher's courses exist
        for teacher_id, teacher_data in self.teachers.items():
            for course_id in teacher_data['courses_handled']:
                if course_id not in self.courses:
                    errors.append(f"Teacher {teacher_id} assigned to non-existent course {course_id}")

        # Check if group's courses exist
        for group_id, group_data in self.groups.items():
            for course_id in group_data['courses']:
                if course_id not in self.courses:
                    errors.append(f"Group {group_id} assigned to non-existent course {course_id}")

        # Check if all courses have teachers
        for course_id in self.courses:
            has_teacher = any(course_id in teacher['courses_handled'] 
                            for teacher in self.teachers.values())
            if not has_teacher:
                errors.append(f"Course {course_id} has no assigned teacher")

        if errors:
            logger.warning(f"Validation found {len(errors)} issues")
        else:
            logger.info("Data validation successful")

        return errors

def create_sample_data():
    """Create sample Excel file for testing"""
    import pandas as pd

    # Sample courses data
    courses_data = {
        'CourseID': ['DDBMS', 'AWS-CCS', 'AI-ML', 'SOFTWARE-TESTING', 'PROJECT'],
        'CourseName': ['Distributed Database Management Systems', 'Cloud Computing with AWS', 
                      'Artificial Intelligence & Machine Learning', 'Software Testing', 'Major Project'],
        'Type': ['TH', 'TH', 'TH', 'LAB', 'PROJECT'],
        'Semester': ['VII-A', 'VII-A', 'VII-B', 'VII-A', 'VII-B'],
        'Duration': [1, 1, 1, 2, 2]
    }

    # Sample teachers data
    teachers_data = {
        'TeacherID': ['T001', 'T002', 'T003', 'T004', 'T005'],
        'TeacherName': ['Dr. Smith', 'Prof. Johnson', 'Dr. Brown', 'Ms. Davis', 'Mr. Wilson'],
        'CoursesHandled': ['DDBMS', 'AWS-CCS', 'AI-ML', 'SOFTWARE-TESTING', 'PROJECT'],
        'Availability': ['', '', 'Monday-Morning', '', '']
    }

    # Sample rooms data
    rooms_data = {
        'RoomID': ['R101', 'R102', 'LAB1', 'LAB2', 'PROJ-ROOM'],
        'Capacity': [60, 60, 30, 30, 25],
        'Type': ['classroom', 'classroom', 'lab', 'lab', 'project room']
    }

    # Sample timeslots data
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    times = ['09:30-10:30', '10:30-11:30', '11:30-12:30', '14:00-15:00', '15:00-16:00', '16:00-17:00']

    timeslots_data = {
        'SlotID': [],
        'Day': [],
        'Time': []
    }

    slot_id = 1
    for day in days:
        for time in times:
            timeslots_data['SlotID'].append(f'S{slot_id:03d}')
            timeslots_data['Day'].append(day)
            timeslots_data['Time'].append(time)
            slot_id += 1

    # Sample groups data
    groups_data = {
        'GroupID': ['AI-VII-A', 'AI-VII-B'],
        'Semester': ['VII-A', 'VII-B'],
        'Courses': ['DDBMS,AWS-CCS,SOFTWARE-TESTING', 'AI-ML,PROJECT']
    }

    # Create Excel file
    with pd.ExcelWriter('sample_input.xlsx', engine='openpyxl') as writer:
        pd.DataFrame(courses_data).to_excel(writer, sheet_name='Courses', index=False)
        pd.DataFrame(teachers_data).to_excel(writer, sheet_name='Teachers', index=False)
        pd.DataFrame(rooms_data).to_excel(writer, sheet_name='Rooms', index=False)
        pd.DataFrame(timeslots_data).to_excel(writer, sheet_name='Timeslots', index=False)
        pd.DataFrame(groups_data).to_excel(writer, sheet_name='Groups', index=False)

    logger.info("Sample Excel file 'sample_input.xlsx' created successfully")import pandas as pd
from typing import Dict, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InputParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.courses = {}
        self.teachers = {}
        self.rooms = {}
        self.timeslots = {}
        self.groups = {}

    def parse_excel(self, excel_file=None) -> Tuple[Dict, Dict, Dict, Dict, Dict]:
        """Parse the Excel file and return structured data"""
        try:
            # Use provided ExcelFile or open a new one
            if excel_file is None:
                excel_file = pd.ExcelFile(self.file_path)

            # Parse courses
            if 'Courses' in excel_file.sheet_names:
                courses_df = pd.read_excel(excel_file, sheet_name='Courses')
                self._parse_courses(courses_df)

            # Parse teachers
            if 'Teachers' in excel_file.sheet_names:
                teachers_df = pd.read_excel(excel_file, sheet_name='Teachers')
                self._parse_teachers(teachers_df)

            # Parse rooms
            if 'Rooms' in excel_file.sheet_names:
                rooms_df = pd.read_excel(excel_file, sheet_name='Rooms')
                self._parse_rooms(rooms_df)

            # Parse timeslots
            if 'Timeslots' in excel_file.sheet_names:
                timeslots_df = pd.read_excel(excel_file, sheet_name='Timeslots')
                self._parse_timeslots(timeslots_df)

            # Parse groups
            if 'Groups' in excel_file.sheet_names:
                groups_df = pd.read_excel(excel_file, sheet_name='Groups')
                self._parse_groups(groups_df)

            logger.info("Successfully parsed Excel file")
            return self.courses, self.teachers, self.rooms, self.timeslots, self.groups

        except Exception as e:
            logger.error(f"Error parsing Excel file: {str(e)}")
            raise e

    def _parse_courses(self, df: pd.DataFrame):
        """Parse courses sheet"""
        required_columns = ['CourseID', 'CourseName', 'Type', 'Semester', 'Duration']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Courses sheet: {missing}")
        
        for _, row in df.iterrows():
            course_id = str(row['CourseID']).strip()
            self.courses[course_id] = {
                'course_name': str(row['CourseName']).strip(),
                'type': str(row['Type']).strip().upper(),
                'semester': str(row['Semester']).strip(),
                'duration': int(row['Duration']) if pd.notna(row['Duration']) else 1
            }
        logger.info(f"Parsed {len(self.courses)} courses")

    def _parse_teachers(self, df: pd.DataFrame):
        """Parse teachers sheet"""
        required_columns = ['TeacherID', 'TeacherName', 'CoursesHandled']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Teachers sheet: {missing}")
        
        for _, row in df.iterrows():
            teacher_id = str(row['TeacherID']).strip()

            # Parse courses handled - can be comma-separated
            courses_handled = []
            if pd.notna(row['CoursesHandled']):
                courses_str = str(row['CoursesHandled']).strip()
                courses_handled = [c.strip() for c in courses_str.split(',') if c.strip()]

            # Parse availability constraints
            availability = []
            if pd.notna(row.get('Availability', '')):
                avail_str = str(row['Availability']).strip()
                if avail_str:
                    availability = [a.strip() for a in avail_str.split(',') if a.strip()]

            self.teachers[teacher_id] = {
                'teacher_name': str(row['TeacherName']).strip(),
                'courses_handled': courses_handled,
                'availability': availability
            }
        logger.info(f"Parsed {len(self.teachers)} teachers")

    def _parse_rooms(self, df: pd.DataFrame):
        """Parse rooms sheet"""
        required_columns = ['RoomID', 'Capacity', 'Type']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Rooms sheet: {missing}")
        
        for _, row in df.iterrows():
            room_id = str(row['RoomID']).strip()
            self.rooms[room_id] = {
                'capacity': int(row['Capacity']) if pd.notna(row['Capacity']) else 50,
                'type': str(row['Type']).strip().lower(),
            }
        logger.info(f"Parsed {len(self.rooms)} rooms")

    def _parse_timeslots(self, df: pd.DataFrame):
        """Parse timeslots sheet"""
        required_columns = ['SlotID', 'Day', 'Time']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Timeslots sheet: {missing}")
        
        for _, row in df.iterrows():
            slot_id = str(row['SlotID']).strip()
            self.timeslots[slot_id] = {
                'day': str(row['Day']).strip(),
                'time': str(row['Time']).strip(),
                'slot_index': len(self.timeslots)  # For ordering
            }
        logger.info(f"Parsed {len(self.timeslots)} timeslots")

    def _parse_groups(self, df: pd.DataFrame):
        """Parse groups sheet"""
        required_columns = ['GroupID', 'Semester', 'Courses']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Groups sheet: {missing}")
        
        for _, row in df.iterrows():
            group_id = str(row['GroupID']).strip()

            # Parse courses for this group
            courses = []
            if pd.notna(row['Courses']):
                courses_str = str(row['Courses']).strip()
                courses = [c.strip() for c in courses_str.split(',') if c.strip()]

            self.groups[group_id] = {
                'semester': str(row['Semester']).strip(),
                'courses': courses
            }
        logger.info(f"Parsed {len(self.groups)} groups")

    def validate_data(self) -> List[str]:
        """Validate parsed data for consistency"""
        errors = []

        # Check if teacher's courses exist
        for teacher_id, teacher_data in self.teachers.items():
            for course_id in teacher_data['courses_handled']:
                if course_id not in self.courses:
                    errors.append(f"Teacher {teacher_id} assigned to non-existent course {course_id}")

        # Check if group's courses exist
        for group_id, group_data in self.groups.items():
            for course_id in group_data['courses']:
                if course_id not in self.courses:
                    errors.append(f"Group {group_id} assigned to non-existent course {course_id}")

        # Check if all courses have teachers
        for course_id in self.courses:
            has_teacher = any(course_id in teacher['courses_handled'] 
                            for teacher in self.teachers.values())
            if not has_teacher:
                errors.append(f"Course {course_id} has no assigned teacher")

        if errors:
            logger.warning(f"Validation found {len(errors)} issues")
        else:
            logger.info("Data validation successful")

        return errors

def create_sample_data():
    """Create sample Excel file for testing"""
    import pandas as pd

    # Sample courses data
    courses_data = {
        'CourseID': ['DDBMS', 'AWS-CCS', 'AI-ML', 'SOFTWARE-TESTING', 'PROJECT'],
        'CourseName': ['Distributed Database Management Systems', 'Cloud Computing with AWS', 
                      'Artificial Intelligence & Machine Learning', 'Software Testing', 'Major Project'],
        'Type': ['TH', 'TH', 'TH', 'LAB', 'PROJECT'],
        'Semester': ['VII-A', 'VII-A', 'VII-B', 'VII-A', 'VII-B'],
        'Duration': [1, 1, 1, 2, 2]
    }

    # Sample teachers data
    teachers_data = {
        'TeacherID': ['T001', 'T002', 'T003', 'T004', 'T005'],
        'TeacherName': ['Dr. Smith', 'Prof. Johnson', 'Dr. Brown', 'Ms. Davis', 'Mr. Wilson'],
        'CoursesHandled': ['DDBMS', 'AWS-CCS', 'AI-ML', 'SOFTWARE-TESTING', 'PROJECT'],
        'Availability': ['', '', 'Monday-Morning', '', '']
    }

    # Sample rooms data
    rooms_data = {
        'RoomID': ['R101', 'R102', 'LAB1', 'LAB2', 'PROJ-ROOM'],
        'Capacity': [60, 60, 30, 30, 25],
        'Type': ['classroom', 'classroom', 'lab', 'lab', 'project room']
    }

    # Sample timeslots data
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    times = ['09:30-10:30', '10:30-11:30', '11:30-12:30', '14:00-15:00', '15:00-16:00', '16:00-17:00']

    timeslots_data = {
        'SlotID': [],
        'Day': [],
        'Time': []
    }

    slot_id = 1
    for day in days:
        for time in times:
            timeslots_data['SlotID'].append(f'S{slot_id:03d}')
            timeslots_data['Day'].append(day)
            timeslots_data['Time'].append(time)
            slot_id += 1

    # Sample groups data
    groups_data = {
        'GroupID': ['AI-VII-A', 'AI-VII-B'],
        'Semester': ['VII-A', 'VII-B'],
        'Courses': ['DDBMS,AWS-CCS,SOFTWARE-TESTING', 'AI-ML,PROJECT']
    }

    # Create Excel file
    with pd.ExcelWriter('sample_input.xlsx', engine='openpyxl') as writer:
        pd.DataFrame(courses_data).to_excel(writer, sheet_name='Courses', index=False)
        pd.DataFrame(teachers_data).to_excel(writer, sheet_name='Teachers', index=False)
        pd.DataFrame(rooms_data).to_excel(writer, sheet_name='Rooms', index=False)
        pd.DataFrame(timeslots_data).to_excel(writer, sheet_name='Timeslots', index=False)
        pd.DataFrame(groups_data).to_excel(writer, sheet_name='Groups', index=False)

    logger.info("Sample Excel file 'sample_input.xlsx' created successfully")import pandas as pd
from typing import Dict, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InputParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.courses = {}
        self.teachers = {}
        self.rooms = {}
        self.timeslots = {}
        self.groups = {}

    def parse_excel(self, excel_file=None) -> Tuple[Dict, Dict, Dict, Dict, Dict]:
        """Parse the Excel file and return structured data"""
        try:
            # Use provided ExcelFile or open a new one
            if excel_file is None:
                excel_file = pd.ExcelFile(self.file_path)

            # Parse courses
            if 'Courses' in excel_file.sheet_names:
                courses_df = pd.read_excel(excel_file, sheet_name='Courses')
                self._parse_courses(courses_df)

            # Parse teachers
            if 'Teachers' in excel_file.sheet_names:
                teachers_df = pd.read_excel(excel_file, sheet_name='Teachers')
                self._parse_teachers(teachers_df)

            # Parse rooms
            if 'Rooms' in excel_file.sheet_names:
                rooms_df = pd.read_excel(excel_file, sheet_name='Rooms')
                self._parse_rooms(rooms_df)

            # Parse timeslots
            if 'Timeslots' in excel_file.sheet_names:
                timeslots_df = pd.read_excel(excel_file, sheet_name='Timeslots')
                self._parse_timeslots(timeslots_df)

            # Parse groups
            if 'Groups' in excel_file.sheet_names:
                groups_df = pd.read_excel(excel_file, sheet_name='Groups')
                self._parse_groups(groups_df)

            logger.info("Successfully parsed Excel file")
            return self.courses, self.teachers, self.rooms, self.timeslots, self.groups

        except Exception as e:
            logger.error(f"Error parsing Excel file: {str(e)}")
            raise e

    def _parse_courses(self, df: pd.DataFrame):
        """Parse courses sheet"""
        required_columns = ['CourseID', 'CourseName', 'Type', 'Semester', 'Duration']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Courses sheet: {missing}")
        
        for _, row in df.iterrows():
            course_id = str(row['CourseID']).strip()
            self.courses[course_id] = {
                'course_name': str(row['CourseName']).strip(),
                'type': str(row['Type']).strip().upper(),
                'semester': str(row['Semester']).strip(),
                'duration': int(row['Duration']) if pd.notna(row['Duration']) else 1
            }
        logger.info(f"Parsed {len(self.courses)} courses")

    def _parse_teachers(self, df: pd.DataFrame):
        """Parse teachers sheet"""
        required_columns = ['TeacherID', 'TeacherName', 'CoursesHandled']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Teachers sheet: {missing}")
        
        for _, row in df.iterrows():
            teacher_id = str(row['TeacherID']).strip()

            # Parse courses handled - can be comma-separated
            courses_handled = []
            if pd.notna(row['CoursesHandled']):
                courses_str = str(row['CoursesHandled']).strip()
                courses_handled = [c.strip() for c in courses_str.split(',') if c.strip()]

            # Parse availability constraints
            availability = []
            if pd.notna(row.get('Availability', '')):
                avail_str = str(row['Availability']).strip()
                if avail_str:
                    availability = [a.strip() for a in avail_str.split(',') if a.strip()]

            self.teachers[teacher_id] = {
                'teacher_name': str(row['TeacherName']).strip(),
                'courses_handled': courses_handled,
                'availability': availability
            }
        logger.info(f"Parsed {len(self.teachers)} teachers")

    def _parse_rooms(self, df: pd.DataFrame):
        """Parse rooms sheet"""
        required_columns = ['RoomID', 'Capacity', 'Type']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Rooms sheet: {missing}")
        
        for _, row in df.iterrows():
            room_id = str(row['RoomID']).strip()
            self.rooms[room_id] = {
                'capacity': int(row['Capacity']) if pd.notna(row['Capacity']) else 50,
                'type': str(row['Type']).strip().lower(),
            }
        logger.info(f"Parsed {len(self.rooms)} rooms")

    def _parse_timeslots(self, df: pd.DataFrame):
        """Parse timeslots sheet"""
        required_columns = ['SlotID', 'Day', 'Time']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Timeslots sheet: {missing}")
        
        for _, row in df.iterrows():
            slot_id = str(row['SlotID']).strip()
            self.timeslots[slot_id] = {
                'day': str(row['Day']).strip(),
                'time': str(row['Time']).strip(),
                'slot_index': len(self.timeslots)  # For ordering
            }
        logger.info(f"Parsed {len(self.timeslots)} timeslots")

    def _parse_groups(self, df: pd.DataFrame):
        """Parse groups sheet"""
        required_columns = ['GroupID', 'Semester', 'Courses']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Groups sheet: {missing}")
        
        for _, row in df.iterrows():
            group_id = str(row['GroupID']).strip()

            # Parse courses for this group
            courses = []
            if pd.notna(row['Courses']):
                courses_str = str(row['Courses']).strip()
                courses = [c.strip() for c in courses_str.split(',') if c.strip()]

            self.groups[group_id] = {
                'semester': str(row['Semester']).strip(),
                'courses': courses
            }
        logger.info(f"Parsed {len(self.groups)} groups")

    def validate_data(self) -> List[str]:
        """Validate parsed data for consistency"""
        errors = []

        # Check if teacher's courses exist
        for teacher_id, teacher_data in self.teachers.items():
            for course_id in teacher_data['courses_handled']:
                if course_id not in self.courses:
                    errors.append(f"Teacher {teacher_id} assigned to non-existent course {course_id}")

        # Check if group's courses exist
        for group_id, group_data in self.groups.items():
            for course_id in group_data['courses']:
                if course_id not in self.courses:
                    errors.append(f"Group {group_id} assigned to non-existent course {course_id}")

        # Check if all courses have teachers
        for course_id in self.courses:
            has_teacher = any(course_id in teacher['courses_handled'] 
                            for teacher in self.teachers.values())
            if not has_teacher:
                errors.append(f"Course {course_id} has no assigned teacher")

        if errors:
            logger.warning(f"Validation found {len(errors)} issues")
        else:
            logger.info("Data validation successful")

        return errors

def create_sample_data():
    """Create sample Excel file for testing"""
    import pandas as pd

    # Sample courses data
    courses_data = {
        'CourseID': ['DDBMS', 'AWS-CCS', 'AI-ML', 'SOFTWARE-TESTING', 'PROJECT'],
        'CourseName': ['Distributed Database Management Systems', 'Cloud Computing with AWS', 
                      'Artificial Intelligence & Machine Learning', 'Software Testing', 'Major Project'],
        'Type': ['TH', 'TH', 'TH', 'LAB', 'PROJECT'],
        'Semester': ['VII-A', 'VII-A', 'VII-B', 'VII-A', 'VII-B'],
        'Duration': [1, 1, 1, 2, 2]
    }

    # Sample teachers data
    teachers_data = {
        'TeacherID': ['T001', 'T002', 'T003', 'T004', 'T005'],
        'TeacherName': ['Dr. Smith', 'Prof. Johnson', 'Dr. Brown', 'Ms. Davis', 'Mr. Wilson'],
        'CoursesHandled': ['DDBMS', 'AWS-CCS', 'AI-ML', 'SOFTWARE-TESTING', 'PROJECT'],
        'Availability': ['', '', 'Monday-Morning', '', '']
    }

    # Sample rooms data
    rooms_data = {
        'RoomID': ['R101', 'R102', 'LAB1', 'LAB2', 'PROJ-ROOM'],
        'Capacity': [60, 60, 30, 30, 25],
        'Type': ['classroom', 'classroom', 'lab', 'lab', 'project room']
    }

    # Sample timeslots data
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    times = ['09:30-10:30', '10:30-11:30', '11:30-12:30', '14:00-15:00', '15:00-16:00', '16:00-17:00']

    timeslots_data = {
        'SlotID': [],
        'Day': [],
        'Time': []
    }

    slot_id = 1
    for day in days:
        for time in times:
            timeslots_data['SlotID'].append(f'S{slot_id:03d}')
            timeslots_data['Day'].append(day)
            timeslots_data['Time'].append(time)
            slot_id += 1

    # Sample groups data
    groups_data = {
        'GroupID': ['AI-VII-A', 'AI-VII-B'],
        'Semester': ['VII-A', 'VII-B'],
        'Courses': ['DDBMS,AWS-CCS,SOFTWARE-TESTING', 'AI-ML,PROJECT']
    }

    # Create Excel file
    with pd.ExcelWriter('sample_input.xlsx', engine='openpyxl') as writer:
        pd.DataFrame(courses_data).to_excel(writer, sheet_name='Courses', index=False)
        pd.DataFrame(teachers_data).to_excel(writer, sheet_name='Teachers', index=False)
        pd.DataFrame(rooms_data).to_excel(writer, sheet_name='Rooms', index=False)
        pd.DataFrame(timeslots_data).to_excel(writer, sheet_name='Timeslots', index=False)
        pd.DataFrame(groups_data).to_excel(writer, sheet_name='Groups', index=False)

    logger.info("Sample Excel file 'sample_input.xlsx' created successfully")
