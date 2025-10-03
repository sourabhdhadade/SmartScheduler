# SmartScheduler - AI-Powered Automated Timetable Generator

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.25.0-red.svg)](https://streamlit.io/)
[![OR-Tools](https://img.shields.io/badge/OR--Tools-9.7-green.svg)](https://developers.google.com/optimization)
[![DEAP](https://img.shields.io/badge/DEAP-1.4.1-orange.svg)](https://github.com/DEAP/deap)

Sourabh Dhadade, Department of Artificial Intelligence , G.H.Raisoni College Of Engineering, Nagpur

[![Sourabh Dhadade](https://img.shields.io/badge/Sourabh_Dhadade-red.svg)](https://github.com/sourabhdhadade/)

Email: sourabhdha367@gmail.com

Mohit Raut, Department of Artificial Intelligence , G.H.Raisoni College Of Engineering, Nagpur

[![Mohit Raut](https://img.shields.io/badge/Mohit_Raut-red.svg)](https://github.com/rmohit9/)

Email: mohitraut009@gmail.com

Harshal Ghoradkar, Department of Artificial Intelligence , G.H.Raisoni College Of Engineering, Nagpur

[![Harshal Ghoradkar](https://img.shields.io/badge/Harshal_Ghoradkar-red.svg)](https://github.com/Harshal279/)

Email: harshalghoradkar2@gmail.com

Anshu pandey, Department of Artificial Intelligence , G.H.Raisoni College Of Engineering, Nagpur

Email: anshupandey1369@gmail.com


SmartScheduler is an AI-powered automated timetable generator designed specifically for higher educational institutes. It uses advanced optimization algorithms combining Google OR-Tools for constraint satisfaction and DEAP genetic algorithms for optimization to create conflict-free, optimized timetables.

## 🌟 Features

### Core Functionality
- **Hard Constraint Satisfaction**: Ensures no teacher/room/group conflicts using OR-Tools CP-SAT solver
- **Soft Constraint Optimization**: Uses DEAP genetic algorithms to minimize gaps, spread subjects evenly, and balance faculty workload
- **Multiple Timetable Views**: Generates class-wise, teacher-wise, and room-wise timetables from the same solution
- **Multi-format Export**: Export timetables to Excel, HTML, and PDF formats
- **Interactive Web Interface**: User-friendly Streamlit-based interface
- **Color-coded Display**: Visual distinction for different course types (Theory=Blue, Practical/Lab=Green, Project=Orange)
- **Timetable Quality Metrics**: Shows Accuracy, Precision, Recall and F1 Score after every generation

### Advanced Features
- **Input Validation**: Comprehensive validation of input data with detailed error reporting
- **Statistics Dashboard**: Real-time statistics about generated timetables
- **Sample Data Generation**: Built-in sample data generator for testing
- **Batch Download**: Download all timetable formats in a single ZIP file
- **Responsive Design**: Works on desktop and mobile devices

## 🚀 Quick Start

### Installation

1. **Clone or download the project files**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the application**:
   ```bash
   streamlit run app.py
   ```
4. **Open your browser** to `http://localhost:8501`

### Basic Usage

1. **Upload Excel File**: Use the sidebar to upload your timetable input file
2. **Generate Timetable**: Click "Generate Timetable" button
3. **View Results**: Browse through different timetable views in tabs
4. **Download**: Export timetables in your preferred format

## 📁 Project Structure

```
SmartScheduler/
├── app.py                 # Streamlit web application
├── input_parser.py        # Excel input file parser and validator
├── scheduler.py           # OR-Tools + DEAP optimization engine
├── output_generator.py    # Timetable generation and export utilities
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── sample_input.xlsx     # Sample input file (generated automatically)
└── outputs/              # Generated timetable files
    ├── class_timetable.xlsx
    ├── teacher_timetable.xlsx
    ├── room_timetable.xlsx
    ├── class_timetable.html
    ├── teacher_timetable.html
    ├── room_timetable.html
    ├── class_timetable.pdf
    ├── teacher_timetable.pdf
    └── room_timetable.pdf
```

## 📊 Input File Format

Your Excel file must contain the following sheets with specific column headers:

### Sheet: Courses
| Column      | Type   | Description                              | Example        |
|-------------|--------|------------------------------------------|----------------|
| CourseID    | String | Unique course identifier                 | DDBMS          |
| CourseName  | String | Full name of the course                  | Distributed DB |
| Type        | String | TH (theory), PR (practical), LAB, PROJECT | TH           |
| Semester    | String | Semester identifier                      | VII-A          |
| Duration    | Integer| Class duration in hours (1 or 2)        | 1              |

### Sheet: Teachers
| Column         | Type   | Description                          | Example           |
|----------------|--------|--------------------------------------|-------------------|
| TeacherID      | String | Unique teacher identifier            | T001              |
| TeacherName    | String | Full name of teacher                 | Dr. Smith         |
| CoursesHandled | String | Comma-separated list of course IDs   | DDBMS,AWS-CCS     |
| Availability   | String | Optional: unavailable times          | Monday-Morning    |

### Sheet: Rooms
| Column   | Type    | Description                    | Example    |
|----------|---------|--------------------------------|------------|
| RoomID   | String  | Unique room identifier         | R101       |
| Capacity | Integer | Seating capacity               | 60         |
| Type     | String  | classroom, lab, project room   | classroom  |

### Sheet: Timeslots
| Column  | Type   | Description              | Example      |
|---------|--------|--------------------------|--------------|
| SlotID  | String | Unique slot identifier   | S001         |
| Day     | String | Day of the week          | Monday       |
| Time    | String | Time range               | 09:30-10:30  |

### Sheet: Groups
| Column   | Type   | Description                        | Example              |
|----------|--------|------------------------------------|----------------------|
| GroupID  | String | Unique group identifier            | AI-VII-A             |
| Semester | String | Semester mapping                   | VII-A                |
| Courses  | String | Comma-separated course IDs         | DDBMS,AWS-CCS,TESTING|

## ⚙️ Algorithm Details

### Constraint Satisfaction (OR-Tools)
SmartScheduler uses Google OR-Tools CP-SAT solver to handle hard constraints:

1. **Teacher Conflicts**: No teacher can be in multiple classes simultaneously
2. **Room Conflicts**: No room can be double-booked
3. **Student Group Conflicts**: No group can have overlapping classes
4. **Room-Course Type Matching**: Labs require lab rooms, theory needs classrooms

### Optimization (DEAP Genetic Algorithm)
After finding a feasible solution, DEAP genetic algorithms optimize for:

1. **Gap Minimization**: Reduces free periods in schedules (weight: 30%)
2. **Even Distribution**: Spreads subjects across the week (weight: 30%)
3. **Workload Balance**: Balances teaching loads among faculty (weight: 40%)

### Optimization Parameters
- Population Size: 20 individuals
- Generations: 10
- Crossover Probability: 0.7
- Mutation Probability: 0.2
- Tournament Selection: Size 3

## 🎯 Usage Examples

### Creating Sample Data
```python
from input_parser import create_sample_data
create_sample_data()  # Creates sample_input.xlsx
```

### Programmatic Usage
```python
from input_parser import InputParser
from scheduler import TimetableScheduler
from output_generator import TimetableGenerator

# Parse input
parser = InputParser('your_file.xlsx')
courses, teachers, rooms, timeslots, groups = parser.parse_excel()

# Generate schedule
scheduler = TimetableScheduler(courses, teachers, rooms, timeslots, groups)
schedule = scheduler.generate_schedule()

# Generate outputs
generator = TimetableGenerator(schedule, courses, teachers, rooms, timeslots, groups)
excel_files = generator.export_to_excel()
html_files = generator.export_to_html()
pdf_files = generator.export_to_pdf()
```

## 🔧 Customization and Extension

### Adding New Constraints
To add custom constraints, modify the `_generate_feasible_schedule()` method in `scheduler.py`:

```python
# Example: No classes on Friday afternoons
for timeslot_id in self.timeslot_ids:
    if (self.timeslots[timeslot_id]['day'] == 'Friday' and 
        'afternoon' in self.timeslots[timeslot_id]['time'].lower()):
        # Add constraint to avoid this timeslot
        pass
```

### Modifying Optimization Weights
Adjust weights in the `_evaluate_schedule()` method:

```python
# Current weights
score += self._evaluate_gaps(schedule) * 0.3          # Gap penalty
score += self._evaluate_distribution(schedule) * 0.3  # Distribution
score += self._evaluate_workload_balance(schedule) * 0.4  # Workload balance
```

### Custom Export Formats
Extend the `TimetableGenerator` class to add new export formats:

```python
def export_to_json(self):
    # Implementation for JSON export
    pass
```

## 🐛 Troubleshooting

### Common Issues

**"Could not find feasible schedule"**
- Check if you have enough rooms for all course types
- Verify that all courses have assigned teachers
- Ensure sufficient timeslots for all courses
- Review availability constraints for conflicts

**"Input validation failed"**
- Check Excel sheet names (must be: Courses, Teachers, Rooms, Timeslots, Groups)
- Verify all required columns are present
- Ensure CourseIDs in Teachers and Groups sheets exist in Courses sheet

**"Performance Issues"**
- Reduce the number of courses or groups for testing
- Increase solver timeout in `scheduler.py`
- Reduce genetic algorithm generations for faster results

### Debug Mode
Enable detailed logging by modifying the logging level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Performance Guidelines

### Recommended Limits
- **Courses**: Up to 50 courses
- **Teachers**: Up to 30 teachers
- **Rooms**: Up to 20 rooms
- **Timeslots**: Up to 36 slots (6 days × 6 periods)
- **Groups**: Up to 10 groups

### Optimization Tips
- Start with smaller datasets to validate constraints
- Use meaningful CourseIDs and TeacherIDs for easier debugging
- Ensure roughly balanced course distribution across groups
- Provide adequate rooms for each course type

## 📄 Dependencies

The application requires the following Python packages:

```
pandas==2.0.3          # Data manipulation and analysis
openpyxl==3.1.2        # Excel file handling
ortools==9.7.2996      # Constraint programming solver
deap==1.4.1            # Genetic algorithm framework
streamlit==1.25.0      # Web application framework
reportlab==4.0.4       # PDF generation
matplotlib==3.7.2      # Plotting (for future enhancements)
numpy==1.24.3          # Numerical computing
```

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/new-feature`
3. **Make changes and test thoroughly**
4. **Update documentation** if needed
5. **Submit a pull request** with detailed description

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd SmartScheduler

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/  # (if tests directory exists)

# Start development server
streamlit run app.py
```

## 📝 License

This project is open-source and available under the MIT License. See LICENSE file for details.

## 🙏 Acknowledgments

- **Google OR-Tools Team** for the excellent constraint programming library
- **DEAP Developers** for the genetic algorithm framework
- **Streamlit Team** for the amazing web app framework
- **Engineering Education Community** for inspiration and requirements

## 📞 Support

For issues, questions, or contributions:

1. **Check existing issues** in the project repository
2. **Create a new issue** with detailed description
3. **Provide sample data** if reporting bugs
4. **Include error logs** for technical issues

---

**SmartScheduler** - Making timetable generation intelligent, efficient, and effortless! 🎓✨
