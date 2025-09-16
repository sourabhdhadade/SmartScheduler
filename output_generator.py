import pandas as pd
import logging
from typing import Dict, List, Any, Tuple
import os
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimetableGenerator:
    def __init__(self, schedule, courses, teachers, rooms, timeslots, groups):
        self.schedule = schedule
        self.courses = courses
        self.teachers = teachers
        self.rooms = rooms
        self.timeslots = timeslots
        self.groups = groups

        # Create ordered lists of days and times
        self.days = self._get_ordered_days()
        self.times = self._get_ordered_times()

        # Color scheme for different course types
        self.color_scheme = {
            'TH': "#0D13A8",      #  blue for theory
            'PR': "#0093A67A",      #  green for practical
            'LAB': "#008000",     #  green for lab
            'PROJECT': "#C47900"  #  orange for project
        }

    def _get_ordered_days(self) -> List[str]:
        """Get ordered list of days"""
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        days_in_schedule = set()

        for timeslot_data in self.timeslots.values():
            days_in_schedule.add(timeslot_data['day'])

        return [day for day in day_order if day in days_in_schedule]

    def _get_ordered_times(self) -> List[str]:
        """Get ordered list of times"""
        times_in_schedule = set()

        for timeslot_data in self.timeslots.values():
            times_in_schedule.add(timeslot_data['time'])

        # Sort times
        time_list = list(times_in_schedule)
        time_list.sort(key=lambda x: x.split('-')[0])  # Sort by start time

        return time_list

    def generate_class_timetable(self) -> pd.DataFrame:
        """Generate class-wise timetable"""
        logger.info("Generating class-wise timetable...")

        # Create empty timetable for each group
        group_timetables = {}

        for group_id in self.groups.keys():
            # Create empty DataFrame
            timetable = pd.DataFrame(index=self.times, columns=self.days)
            timetable = timetable.fillna('')

            if group_id in self.schedule:
                for course_id, assignment in self.schedule[group_id].items():
                    timeslot_id = assignment['timeslot']
                    teacher_id = assignment['teacher']
                    room_id = assignment['room']

                    # Get timeslot details
                    if timeslot_id in self.timeslots:
                        day = self.timeslots[timeslot_id]['day']
                        time = self.timeslots[timeslot_id]['time']

                        # Get course name and teacher name
                        course_name = self.courses.get(course_id, {}).get('course_name', course_id)
                        teacher_name = self.teachers.get(teacher_id, {}).get('teacher_name', teacher_id)

                        # Format cell content
                        cell_content = f"{course_id}\n{teacher_name}\n{room_id}"

                        if day in timetable.columns and time in timetable.index:
                            timetable.loc[time, day] = cell_content

            group_timetables[group_id] = timetable

        return group_timetables

    def generate_teacher_timetable(self) -> pd.DataFrame:
        """Generate teacher-wise timetable"""
        logger.info("Generating teacher-wise timetable...")

        teacher_timetables = {}

        for teacher_id in self.teachers.keys():
            # Create empty DataFrame
            timetable = pd.DataFrame(index=self.times, columns=self.days)
            timetable = timetable.fillna('')

            # Fill assignments for this teacher
            for group_id in self.schedule:
                for course_id, assignment in self.schedule[group_id].items():
                    if assignment['teacher'] == teacher_id:
                        timeslot_id = assignment['timeslot']
                        room_id = assignment['room']

                        # Get timeslot details
                        if timeslot_id in self.timeslots:
                            day = self.timeslots[timeslot_id]['day']
                            time = self.timeslots[timeslot_id]['time']

                            # Format cell content
                            cell_content = f"{group_id}\n{course_id}\n{room_id}"

                            if day in timetable.columns and time in timetable.index:
                                timetable.loc[time, day] = cell_content

            teacher_timetables[teacher_id] = timetable

        return teacher_timetables

    def generate_room_timetable(self) -> pd.DataFrame:
        """Generate room-wise timetable"""
        logger.info("Generating room-wise timetable...")

        room_timetables = {}

        for room_id in self.rooms.keys():
            # Create empty DataFrame
            timetable = pd.DataFrame(index=self.times, columns=self.days)
            timetable = timetable.fillna('')

            # Fill assignments for this room
            for group_id in self.schedule:
                for course_id, assignment in self.schedule[group_id].items():
                    if assignment['room'] == room_id:
                        timeslot_id = assignment['timeslot']
                        teacher_id = assignment['teacher']

                        # Get timeslot details
                        if timeslot_id in self.timeslots:
                            day = self.timeslots[timeslot_id]['day']
                            time = self.timeslots[timeslot_id]['time']

                            # Get teacher name
                            teacher_name = self.teachers.get(teacher_id, {}).get('teacher_name', teacher_id)

                            # Format cell content
                            cell_content = f"{group_id}\n{course_id}\n{teacher_name}"

                            if day in timetable.columns and time in timetable.index:
                                timetable.loc[time, day] = cell_content

            room_timetables[room_id] = timetable

        return room_timetables

    def export_to_excel(self, output_dir='outputs'):
        """Export all timetables to Excel files"""
        logger.info("Exporting timetables to Excel...")

        os.makedirs(output_dir, exist_ok=True)

        # Generate timetables
        class_timetables = self.generate_class_timetable()
        teacher_timetables = self.generate_teacher_timetable()
        room_timetables = self.generate_room_timetable()

        # Export class timetables
        class_file = os.path.join(output_dir, 'class_timetable.xlsx')
        with pd.ExcelWriter(class_file, engine='openpyxl') as writer:
            for group_id, timetable in class_timetables.items():
                timetable.to_excel(writer, sheet_name=f'Class_{group_id}')

        # Export teacher timetables
        teacher_file = os.path.join(output_dir, 'teacher_timetable.xlsx')
        with pd.ExcelWriter(teacher_file, engine='openpyxl') as writer:
            for teacher_id, timetable in teacher_timetables.items():
                teacher_name = self.teachers.get(teacher_id, {}).get('teacher_name', teacher_id)
                sheet_name = f'{teacher_id}_{teacher_name}'[:31]  # Excel sheet name limit
                timetable.to_excel(writer, sheet_name=sheet_name)

        # Export room timetables
        room_file = os.path.join(output_dir, 'room_timetable.xlsx')
        with pd.ExcelWriter(room_file, engine='openpyxl') as writer:
            for room_id, timetable in room_timetables.items():
                timetable.to_excel(writer, sheet_name=f'Room_{room_id}')

        logger.info(f"Excel files exported to {output_dir}")

        return {
            'class': class_file,
            'teacher': teacher_file,
            'room': room_file
        }

    def export_to_html(self, output_dir='outputs'):
        """Export all timetables to HTML files"""
        logger.info("Exporting timetables to HTML...")

        os.makedirs(output_dir, exist_ok=True)

        # Generate timetables
        class_timetables = self.generate_class_timetable()
        teacher_timetables = self.generate_teacher_timetable()
        room_timetables = self.generate_room_timetable()

        html_files = {}

        # Export class timetables
        class_file = os.path.join(output_dir, 'class_timetable.html')
        self._export_timetables_to_html(class_timetables, class_file, "Class Timetables")
        html_files['class'] = class_file

        # Export teacher timetables
        teacher_file = os.path.join(output_dir, 'teacher_timetable.html')
        teacher_names = {tid: self.teachers[tid]['teacher_name'] for tid in self.teachers}
        self._export_timetables_to_html(teacher_timetables, teacher_file, "Teacher Timetables", teacher_names)
        html_files['teacher'] = teacher_file

        # Export room timetables
        room_file = os.path.join(output_dir, 'room_timetable.html')
        self._export_timetables_to_html(room_timetables, room_file, "Room Timetables")
        html_files['room'] = room_file

        logger.info(f"HTML files exported to {output_dir}")
        return html_files

    def _export_timetables_to_html(self, timetables: Dict[str, pd.DataFrame], 
                                   filename: str, title: str, name_mapping: Dict = None):
        """Export timetables to HTML with styling"""

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                }}
                h1 {{
                    color: #333;
                    text-align: center;
                }}
                h2 {{
                    color: #666;
                    border-bottom: 2px solid #ddd;
                    padding-bottom: 10px;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin-bottom: 30px;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: center;
                    vertical-align: middle;
                    min-width: 100px;
                    height: 60px;
                }}
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
                .theory {{
                    background-color: #E3F2FD;
                }}
                .practical {{
                    background-color: #E8F5E8;
                }}
                .project {{
                    background-color: #FFF3E0;
                }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
        """

        for entity_id, timetable in timetables.items():
            display_name = entity_id
            if name_mapping and entity_id in name_mapping:
                display_name = f"{entity_id} - {name_mapping[entity_id]}"

            html_content += f"<h2>{display_name}</h2>\n"

            # Convert DataFrame to HTML with custom styling
            table_html = timetable.to_html(classes='timetable', escape=False)

            # Add color coding based on content
            for course_type in ['TH', 'PR', 'LAB', 'PROJECT']:
                color_class = 'theory' if course_type == 'TH' else ('practical' if course_type in ['PR', 'LAB'] else 'project')
                table_html = table_html.replace(f'>{course_type}', f' class="{color_class}">{course_type}')

            html_content += table_html + "\n"

        html_content += """
        </body>
        </html>
        """

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def export_to_pdf(self, output_dir='outputs'):
        """Export all timetables to PDF files"""
        logger.info("Exporting timetables to PDF...")

        os.makedirs(output_dir, exist_ok=True)

        # Generate timetables
        class_timetables = self.generate_class_timetable()
        teacher_timetables = self.generate_teacher_timetable()
        room_timetables = self.generate_room_timetable()

        pdf_files = {}

        # Export class timetables
        class_file = os.path.join(output_dir, 'class_timetable.pdf')
        self._export_timetables_to_pdf(class_timetables, class_file, "Class Timetables")
        pdf_files['class'] = class_file

        # Export teacher timetables
        teacher_file = os.path.join(output_dir, 'teacher_timetable.pdf')
        teacher_names = {tid: self.teachers[tid]['teacher_name'] for tid in self.teachers}
        self._export_timetables_to_pdf(teacher_timetables, teacher_file, "Teacher Timetables", teacher_names)
        pdf_files['teacher'] = teacher_file

        # Export room timetables
        room_file = os.path.join(output_dir, 'room_timetable.pdf')
        self._export_timetables_to_pdf(room_timetables, room_file, "Room Timetables")
        pdf_files['room'] = room_file

        logger.info(f"PDF files exported to {output_dir}")
        return pdf_files

    def _export_timetables_to_pdf(self, timetables: Dict[str, pd.DataFrame], 
                                  filename: str, title: str, name_mapping: Dict = None):
        """Export timetables to PDF"""

        doc = SimpleDocTemplate(filename, pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_para = Paragraph(f"<b>{title}</b>", styles['Title'])
        story.append(title_para)
        story.append(Spacer(1, 0.3*inch))

        for entity_id, timetable in timetables.items():
            display_name = entity_id
            if name_mapping and entity_id in name_mapping:
                display_name = f"{entity_id} - {name_mapping[entity_id]}"

            # Section header
            header = Paragraph(f"<b>{display_name}</b>", styles['Heading2'])
            story.append(header)
            story.append(Spacer(1, 0.1*inch))

            # Convert DataFrame to table data
            table_data = []

            # Header row
            header_row = ['Time'] + list(timetable.columns)
            table_data.append(header_row)

            # Data rows
            for time in timetable.index:
                row = [time]
                for day in timetable.columns:
                    cell_value = timetable.loc[time, day]
                    # Split long text into multiple lines
                    if len(str(cell_value)) > 20:
                        cell_value = str(cell_value).replace('\n', '<br/>')
                    row.append(cell_value)
                table_data.append(row)

            # Create table
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTSIZE', (0, 1), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))

            story.append(table)
            story.append(Spacer(1, 0.3*inch))

        # Build PDF
        doc.build(story)

    def generate_summary_statistics(self) -> Dict[str, Any]:
        """Generate summary statistics about the timetable"""
        logger.info("Generating summary statistics...")

        stats = {
            'total_classes': 0,
            'classes_by_type': {},
            'teacher_workload': {},
            'room_utilization': {},
            'group_schedules': {},
            'time_distribution': {}
        }

        # Count classes by type and calculate statistics
        for group_id in self.schedule:
            group_classes = 0
            for course_id, assignment in self.schedule[group_id].items():
                stats['total_classes'] += 1
                group_classes += 1

                # Course type statistics
                course_type = self.courses.get(course_id, {}).get('type', 'UNKNOWN')
                stats['classes_by_type'][course_type] = stats['classes_by_type'].get(course_type, 0) + 1

                # Teacher workload
                teacher_id = assignment['teacher']
                stats['teacher_workload'][teacher_id] = stats['teacher_workload'].get(teacher_id, 0) + 1

                # Room utilization
                room_id = assignment['room']
                stats['room_utilization'][room_id] = stats['room_utilization'].get(room_id, 0) + 1

                # Time distribution
                timeslot_id = assignment['timeslot']
                day = self.timeslots[timeslot_id]['day']
                stats['time_distribution'][day] = stats['time_distribution'].get(day, 0) + 1

            stats['group_schedules'][group_id] = group_classes

        return stats

def test_output_generator():
    """Test the output generator with sample data"""
    from input_parser import create_sample_data, InputParser
    from scheduler import TimetableScheduler

    # Create sample data and generate schedule
    create_sample_data()
    parser = InputParser('sample_input.xlsx')
    courses, teachers, rooms, timeslots, groups = parser.parse_excel()

    scheduler = TimetableScheduler(courses, teachers, rooms, timeslots, groups)
    schedule = scheduler.generate_schedule()

    if schedule:
        # Generate outputs
        generator = TimetableGenerator(schedule, courses, teachers, rooms, timeslots, groups)

        # Export to all formats
        excel_files = generator.export_to_excel()
        html_files = generator.export_to_html()
        pdf_files = generator.export_to_pdf()

        # Generate statistics
        stats = generator.generate_summary_statistics()

        print("Output generation completed!")
        print(f"Excel files: {excel_files}")
        print(f"HTML files: {html_files}")
        print(f"PDF files: {pdf_files}")
        print(f"Total classes scheduled: {stats['total_classes']}")
        print(f"Classes by type: {stats['classes_by_type']}")
    else:
        print("No schedule to generate outputs for")

if __name__ == "__main__":
    test_output_generator()
