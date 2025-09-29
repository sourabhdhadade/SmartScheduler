import streamlit as st
import pandas as pd
import os
import logging
from datetime import datetime
import zipfile
import io
import tempfile
import time
import re

from input_parser import InputParser
from scheduler import TimetableScheduler
from output_generator import TimetableGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="SmartScheduler - AI Timetable Generator",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #555;
        margin-bottom: 1rem;
    }
    .timetable-cell {
        padding: 8px;
        margin: 2px;
        border-radius: 4px;
        text-align: center;
        font-size: 0.8rem;
        color: #000000;
    }
    .theory {
        background-color: #4FC3F7;
        border: 1px solid #2196F3;
        color: #000000;
    }
    .practical {
        background-color: #4CAF50;
        border: 1px solid #4CAF50;
        color: #000000;
    }
    .lab {
        background-color: #4CAF50;
        border: 1px solid #4CAF50;
        color: #000000;
    }
    .project {
        background-color: #FFB300;
        border: 1px solid #FF9800;
        color: #000000;
    }
    .stats-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    /* Ensure timetable cells are not overridden by Streamlit theme */
    .stDataFrame [data-testid="stTable"] td {
        background-color: inherit !important;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application function"""

    # Initialize session state
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = None
    if 'timetable_data' not in st.session_state:
        st.session_state.timetable_data = None
    if 'selected_teacher' not in st.session_state:
        st.session_state.selected_teacher = None

    # Header
    st.markdown('<h1 class="main-header">🗓️ SmartScheduler</h1>', unsafe_allow_html=True)
    st.markdown('<h3 style="text-align: center; color: #666;">Automated Timetable Generator for Higher Educational Institutes Using OR-Tools and the DEAP Python Library</h3>', 
                unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("📊 Navigation")

        # File upload
        st.subheader("📁 Upload Input File")
        uploaded_file = st.file_uploader(
            "Choose Excel file",
            type=['xlsx', 'xls'],
            help="Upload an Excel file with Courses, Teachers, Rooms, Timeslots, and Groups sheets"
        )

        # Generate button
        generate_button = st.button("🚀 Generate Timetable", type="primary", use_container_width=True)

        st.markdown("---")

        # Sample file download
        st.subheader("📋 Sample Input File")
        if st.button("📥 Create Sample File", use_container_width=True):
            create_sample_file()
            st.success("Sample file created successfully!")

        if os.path.exists('sample_input.xlsx'):
            with open('sample_input.xlsx', 'rb') as f:
                st.download_button(
                    label="⬇️ Download Sample",
                    data=f.read(),
                    file_name="sample_input.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

        # Color legend
        st.subheader("🎨 Color Legend")
        st.markdown("""
        <div style="margin: 0.5rem 0;">
            <div class="timetable-cell theory">Theory (TH)</div>
        </div>
        <div style="margin: 0.5rem 0;">
            <div class="timetable-cell practical">Practical/Lab (PR/LAB)</div>
        </div>
        <div style="margin: 0.5rem 0;">
            <div class="timetable-cell project">Project</div>
        </div>
        """, unsafe_allow_html=True)

    # Main content
    if uploaded_file is not None and generate_button:
        st.session_state.active_tab = None  # Reset tab on new generation
        st.session_state.selected_teacher = None
        generate_timetable_workflow(uploaded_file)
    elif st.session_state.timetable_data is not None:
        # Display timetable results if data exists
        generator, stats, excel_files, html_files, pdf_files = st.session_state.timetable_data
        display_timetable_results(generator, stats, excel_files, html_files, pdf_files)
    elif os.path.exists('outputs') and any(os.listdir('outputs')):
        display_existing_timetables()
    else:
        display_welcome_screen()

def create_sample_file():
    """Create and save sample input file"""
    from input_parser import create_sample_data
    create_sample_data()

def generate_timetable_workflow(uploaded_file):
    """Main workflow for generating timetables"""

    # Use a temporary file to avoid permission issues
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file_obj:
        temp_file_obj.write(uploaded_file.getbuffer())
        temp_file = temp_file_obj.name

    try:
        with st.spinner("🔍 Parsing input file..."):
            # Parse input file
            parser = InputParser(temp_file)
            with pd.ExcelFile(temp_file) as excel_file:
                courses, teachers, rooms, timeslots, groups = parser.parse_excel(excel_file=excel_file)

            # Validate data
            errors = parser.validate_data()
            if errors:
                st.error("❌ Input validation failed!")
                st.subheader("Validation Errors:")
                for error in errors:
                    st.error(f"• {error}")
                return
            else:
                st.success("✅ Input file validated successfully!")

            # Log courses dictionary for debugging
            logger.info(f"Courses dictionary: {courses}")

        # Display input summary
        display_input_summary(courses, teachers, rooms, timeslots, groups)

        with st.spinner("🧠 Generating optimized timetable... This may take a few moments."):
            # Generate schedule
            scheduler = TimetableScheduler(courses, teachers, rooms, timeslots, groups)
            schedule = scheduler.generate_schedule()

            if schedule is None:
                st.error("❌ Failed to generate timetable. Please check your constraints and data.")
                return

            st.success("✅ Timetable generated successfully!")
            # Log schedule for debugging
            logger.info(f"Generated schedule: {schedule}")

        with st.spinner("📊 Generating output files..."):
            # Generate outputs
            generator = TimetableGenerator(schedule, courses, teachers, rooms, timeslots, groups)

            # Export to all formats
            excel_files = generator.export_to_excel()
            html_files = generator.export_to_html()
            pdf_files = generator.export_to_pdf()

            # Generate statistics
            stats = generator.generate_summary_statistics()

        st.success("✅ All output files generated successfully!")

        # Store timetable data in session state
        st.session_state.timetable_data = (generator, stats, excel_files, html_files, pdf_files)

        # Display results
        display_timetable_results(generator, stats, excel_files, html_files, pdf_files)

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        logger.error(f"Error in timetable generation: {str(e)}", exc_info=True)
    finally:
        # Clean up temporary file with retry mechanism
        if os.path.exists(temp_file):
            for attempt in range(5):
                try:
                    os.remove(temp_file)
                    logger.info(f"Successfully deleted temporary file: {temp_file}")
                    break
                except PermissionError:
                    logger.warning(f"PermissionError on attempt {attempt + 1} to delete {temp_file}, retrying...")
                    time.sleep(1)
            else:
                logger.error(f"Failed to delete {temp_file} after 5 attempts. Please check if it's open in another program.")
                st.warning("Could not delete temporary file. It may still be in use.")

def display_input_summary(courses, teachers, rooms, timeslots, groups):
    """Display summary of input data"""

    st.subheader("📋 Input Data Summary")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Courses", len(courses))
    with col2:
        st.metric("Teachers", len(teachers))
    with col3:
        st.metric("Rooms", len(rooms))
    with col4:
        st.metric("Time Slots", len(timeslots))
    with col5:
        st.metric("Groups", len(groups))

    # Course types breakdown
    course_types = {}
    for course_data in courses.values():
        course_type = course_data['type']
        course_types[course_type] = course_types.get(course_type, 0) + 1

    if course_types:
        st.subheader("📚 Course Types Distribution")
        type_cols = st.columns(len(course_types))
        for i, (course_type, count) in enumerate(course_types.items()):
            with type_cols[i]:
                st.metric(f"{course_type} Courses", count)

def display_timetable_results(generator, stats, excel_files, html_files, pdf_files):
    """Display generated timetable results"""

    # Statistics
    st.subheader("📊 Generation Statistics")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Classes Scheduled", stats['total_classes'])
    with col2:
        avg_workload = sum(stats['teacher_workload'].values()) / len(stats['teacher_workload']) if stats['teacher_workload'] else 0
        st.metric("Avg Teacher Workload", f"{avg_workload:.1f}")
    with col3:
        avg_utilization = sum(stats['room_utilization'].values()) / len(stats['room_utilization']) if stats['room_utilization'] else 0
        st.metric("Avg Room Utilization", f"{avg_utilization:.1f}")

    # Calculate metrics
    metrics = generator.calculate_metrics()
    st.subheader("📈 Timetable Quality Metrics")
    st.write(f"Accuracy: {metrics['accuracy']:.2f}")
    st.write(f"Precision: {metrics['precision']:.2f}")
    st.write(f"Recall: {metrics['recall']:.2f}")
    st.write(f"F1 Score: {metrics['f1_score']:.2f}")

    # Timetable views
    st.subheader("📅 Timetable Views")

    # Set default tab to 'Teacher-wise' if previously selected
    tab_names = ["🎓 Class-wise", "👨‍🏫 Teacher-wise", "🏢 Room-wise"]
    default_tab = tab_names.index(st.session_state.active_tab) if st.session_state.active_tab in tab_names else 0
    tab1, tab2, tab3 = st.tabs(tab_names)

    with tab1:
        st.session_state.active_tab = tab_names[0]
        display_class_timetables(generator, metrics)

    with tab2:
        st.session_state.active_tab = tab_names[1]
        display_teacher_timetables(generator, metrics)

    with tab3:
        st.session_state.active_tab = tab_names[2]
        display_room_timetables(generator, metrics)

    # Download section
    st.subheader("📥 Download Timetables")

    download_col1, download_col2, download_col3, download_col4 = st.columns(4)

    with download_col1:
        create_download_button("Excel Files", excel_files, "xlsx")

    with download_col2:
        create_download_button("HTML Files", html_files, "html")

    with download_col3:
        create_download_button("PDF Files", pdf_files, "pdf")

    with download_col4:
        if st.button("📦 Download All", use_container_width=True):
            create_zip_download(excel_files, html_files, pdf_files)

def display_class_timetables(generator, metrics):
    """Display class-wise timetables"""
    class_timetables = generator.generate_class_timetable()

    for group_id, timetable in class_timetables.items():
        st.markdown(f"### 🎓 Group: {group_id}")
        # Log timetable cell content for debugging
        logger.info(f"Timetable cell content for {group_id}: {timetable.values}")
        # Style the dataframe
        styled_df = style_timetable_dataframe(timetable, generator.courses)
        st.dataframe(styled_df, use_container_width=True, height=400)
        # Display metrics chart
        display_metrics_chart(metrics, f"Metrics for Group {group_id}")

def display_teacher_timetables(generator, metrics):
    """Display teacher-wise timetables"""
    teacher_timetables = generator.generate_teacher_timetable()

    # Teacher selection
    teacher_ids = list(teacher_timetables.keys())
    if teacher_ids:
        # Use session state to persist teacher selection
        default_teacher = st.session_state.selected_teacher if st.session_state.selected_teacher in teacher_ids else teacher_ids[0]
        selected_teacher = st.selectbox(
            "Select Teacher:",
            teacher_ids,
            index=teacher_ids.index(default_teacher) if default_teacher in teacher_ids else 0,
            format_func=lambda x: f"{x} - {generator.teachers[x]['teacher_name']}",
            key="teacher_select"
        )

        # Update session state with selected teacher
        st.session_state.selected_teacher = selected_teacher

        if selected_teacher:
            st.markdown(f"### 👨‍🏫 Teacher: {generator.teachers[selected_teacher]['teacher_name']} ({selected_teacher})")

            timetable = teacher_timetables[selected_teacher]
            # Log timetable cell content for debugging
            logger.info(f"Teacher timetable cell content for {selected_teacher}: {timetable.values}")
            styled_df = style_timetable_dataframe(timetable, generator.courses)
            st.dataframe(styled_df, use_container_width=True, height=400)
            # Display metrics chart
            display_metrics_chart(metrics, f"Metrics for Teacher {selected_teacher}")
    else:
        st.warning("No teachers available to display.")

def display_room_timetables(generator, metrics):
    """Display room-wise timetables"""
    room_timetables = generator.generate_room_timetable()

    # Room selection
    room_ids = list(room_timetables.keys())
    if room_ids:
        selected_room = st.selectbox("Select Room:", room_ids)

        if selected_room:
            room_info = generator.rooms[selected_room]
            st.markdown(f"### 🏢 Room: {selected_room} (Capacity: {room_info['capacity']}, Type: {room_info['type'].title()})")

            timetable = room_timetables[selected_room]
            # Log timetable cell content for debugging
            logger.info(f"Room timetable cell content for {selected_room}: {timetable.values}")
            styled_df = style_timetable_dataframe(timetable, generator.courses)
            st.dataframe(styled_df, use_container_width=True, height=400)
            # Display metrics chart
            display_metrics_chart(metrics, f"Metrics for Room {selected_room}")
    else:
        st.warning("No rooms available to display.")

def style_timetable_dataframe(df, courses):
    """Style timetable dataframe with colors matching course types"""
    def color_cells(val):
        if pd.isna(val) or val == '':
            return 'background-color: transparent;'
        lines = str(val).split('\n')
        if lines:
            # Extract base course_id by removing _partX and instance suffixes (e.g., _1, _2)
            course_id = lines[0].split('_part')[0]
            base_course_id = re.sub(r'_\d+$', '', course_id)
            logger.info(f"Extracted course_id: {course_id}, Base course_id: {base_course_id}, Cell content: {val}")
            if base_course_id in courses:
                course_type = str(courses[base_course_id]['type']).upper()
                logger.info(f"Styling course ID: {base_course_id}, Type: {course_type}")
                color_map = {
                    'TH': 'background-color: #4FC3F7; border: 1px solid #2196F3; color: #000000;',
                    'PR': 'background-color: #4CAF50; border: 1px solid #4CAF50; color: #000000;',
                    'LAB': 'background-color: #4CAF50; border: 1px solid #4CAF50; color: #000000;',
                    'PROJECT': 'background-color: #FFB300; border: 1px solid #FF9800; color: #000000;'
                }
                if course_type not in color_map:
                    logger.warning(f"Unrecognized course type: {course_type} for course ID: {base_course_id}")
                    return 'background-color: #D3D3D3; border: 1px solid #A9A9A9; color: #000000;'
                return color_map[course_type]
            logger.warning(f"Course ID not found: {base_course_id}")
            return 'background-color: #1E90FF; border: 1px solid #0000CD; color: #FFFFFF;'
        return 'background-color: transparent;'

    # Use applymap for compatibility with older pandas versions
    return df.style.applymap(color_cells)

def display_metrics_chart(metrics, title):
    """Display a bar chart for accuracy, precision, recall, and F1 score"""
    chart_id = f"chart-{title.replace(' ', '-').lower()}-{int(datetime.now().timestamp())}"
    chart_html = f"""
    <canvas id="{chart_id}" width="400" height="200"></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        var ctx = document.getElementById('{chart_id}').getContext('2d');
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: ['Accuracy', 'Precision', 'Recall', 'F1 Score'],
                datasets: [{{
                    label: 'Metrics',
                    data: [{metrics['accuracy']}, {metrics['precision']}, {metrics['recall']}, {metrics['f1_score']}],
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.8)',  // Blue
                        'rgba(75, 192, 192, 0.8)',  // Green
                        'rgba(255, 159, 64, 0.8)',  // Orange
                        'rgba(153, 102, 255, 0.8)'  // Purple
                    ],
                    borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(255, 159, 64, 1)',
                        'rgba(153, 102, 255, 1)'
                    ],
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }},
                    title: {{ display: true, text: '{title}' }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 1,
                        title: {{ display: true, text: 'Score' }}
                    }},
                    x: {{
                        title: {{ display: true, text: 'Metric' }}
                    }}
                }}
            }}
        }});
    </script>
    """
    st.markdown(chart_html, unsafe_allow_html=True)

def create_download_button(label, files, file_type):
    """Create download button for file type"""
    if files:
        # Create a zip file with all files of this type
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_key, file_path in files.items():
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        zip_file.write(file_path, os.path.basename(file_path))

        zip_buffer.seek(0)

        st.download_button(
            label=f"📄 {label}",
            data=zip_buffer.getvalue(),
            file_name=f"timetables_{file_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip",
            use_container_width=True
        )

def create_zip_download(excel_files, html_files, pdf_files):
    """Create download for all files"""
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add all files
        all_files = {**excel_files, **html_files, **pdf_files}

        for file_key, file_path in all_files.items():
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    zip_file.write(file_path, os.path.basename(file_path))

    zip_buffer.seek(0)

    st.download_button(
        label="📦 Download All Files",
        data=zip_buffer.getvalue(),
        file_name=f"all_timetables_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
        mime="application/zip",
        use_container_width=True
    )

def display_existing_timetables():
    """Display existing timetables if available"""
    st.info("📂 Found existing timetable files. Upload a new file to regenerate.")

    # List existing files
    if os.path.exists('outputs'):
        files = os.listdir('outputs')
        if files:
            st.subheader("📁 Existing Files")

            for file in files:
                file_path = os.path.join('outputs', file)
                file_size = os.path.getsize(file_path)

                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.text(file)
                with col2:
                    st.text(f"{file_size} bytes")
                with col3:
                    with open(file_path, 'rb') as f:
                        st.download_button(
                            "⬇️",
                            data=f.read(),
                            file_name=file,
                            key=f"download_{file}"
                        )

def display_welcome_screen():
    """Display welcome screen with instructions"""
    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        ## 🚀 Welcome to SmartScheduler

        SmartScheduler is an AI-powered automated timetable generator designed specifically for higher educational institutes. 
        It uses advanced optimization algorithms (OR-Tools + DEAP) to create conflict-free, optimized timetables.

        ### ✨ Features:
        - **Hard Constraint Satisfaction**: No teacher/room/group conflicts
        - **Soft Constraint Optimization**: Minimizes gaps, balances workload
        - **Multiple Views**: Class-wise, Teacher-wise, and Room-wise timetables
        - **Multiple Formats**: Export to Excel, HTML, and PDF
        - **Color-coded Display**: Visual distinction for different course types
        - **Timetable Quality Metrics**: Shows Accuracy, Precision, Recall and F1 Score after every generation

        ### 📁 Input Format:
        Your Excel file should contain these sheets:
        - **Courses**: CourseID, CourseName, Type, Semester, Duration
        - **Teachers**: TeacherID, TeacherName, CoursesHandled, Availability
        - **Rooms**: RoomID, Capacity, Type
        - **Timeslots**: SlotID, Day, Time
        - **Groups**: GroupID, Semester, Courses

        ### 🎯 How to Use:
        1. Upload your Excel file using the sidebar
        2. Click "Generate Timetable" 
        3. View and download your optimized timetables

        **Don't have an input file?** Create and download our sample file from the sidebar!
        """)

    with col2:
        st.markdown("""
        ### 🎓 Final Year Project (B.Tech AI)
        """)

        st.markdown("### 🎨 Course Color Coding")
        st.markdown("""
        <div style="margin: 0.5rem 0;">
            <div class="timetable-cell theory" style="display: inline-block; width: 100px; margin: 2px;">Theory</div>
        </div>
        <div style="margin: 0.5rem 0;">
            <div class="timetable-cell practical" style="display: inline-block; width: 100px; margin: 2px;">Lab/Practical</div>
        </div>
        <div style="margin: 0.5rem 0;">
            <div class="timetable-cell project" style="display: inline-block; width: 100px; margin: 2px;">Project</div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
