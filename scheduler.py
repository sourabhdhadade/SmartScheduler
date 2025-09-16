import logging
from ortools.sat.python import cp_model
from deap import base, creator, tools, algorithms
import random
import numpy as np
from typing import Dict, List, Tuple, Any
import copy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimetableScheduler:
    def __init__(self, courses, teachers, rooms, timeslots, groups):
        self.courses = courses
        self.teachers = teachers
        self.rooms = rooms
        self.timeslots = timeslots
        self.groups = groups

        # Create mapping dictionaries for easier lookup
        self.course_ids = list(courses.keys())
        self.teacher_ids = list(teachers.keys())
        self.room_ids = list(rooms.keys())
        self.timeslot_ids = list(timeslots.keys())
        self.group_ids = list(groups.keys())

        self.schedule = None

    def generate_schedule(self) -> Dict[str, Any]:
        """Generate optimized timetable using OR-Tools + DEAP"""
        logger.info("Starting timetable generation...")

        # Step 1: Generate feasible solution using OR-Tools
        base_schedule = self._generate_feasible_schedule()

        if base_schedule is None:
            logger.error("Could not find feasible schedule")
            return None

        # Step 2: Optimize using DEAP genetic algorithm
        optimized_schedule = self._optimize_schedule(base_schedule)

        self.schedule = optimized_schedule
        logger.info("Timetable generation completed successfully")

        return optimized_schedule

    def _generate_feasible_schedule(self) -> Dict[str, Any]:
        """Generate feasible schedule using OR-Tools CP-SAT"""
        model = cp_model.CpModel()

        # Variables: assignment[group][course][timeslot][teacher][room] = 1 if assigned
        assignments = {}

        # Create variables for each possible assignment
        for group_id in self.group_ids:
            assignments[group_id] = {}
            group_courses = self.groups[group_id]['courses']

            for course_id in group_courses:
                if course_id not in self.course_ids:
                    continue

                assignments[group_id][course_id] = {}
                course_duration = self.courses[course_id]['duration']
                course_type = self.courses[course_id]['type']

                # Find suitable teachers for this course
                suitable_teachers = [t for t in self.teacher_ids 
                                   if course_id in self.teachers[t]['courses_handled']]

                # Find suitable rooms for this course
                suitable_rooms = self._get_suitable_rooms(course_type)

                for timeslot_id in self.timeslot_ids:
                    assignments[group_id][course_id][timeslot_id] = {}

                    for teacher_id in suitable_teachers:
                        assignments[group_id][course_id][timeslot_id][teacher_id] = {}

                        for room_id in suitable_rooms:
                            var_name = f"{group_id}_{course_id}_{timeslot_id}_{teacher_id}_{room_id}"
                            assignments[group_id][course_id][timeslot_id][teacher_id][room_id] =                                 model.NewBoolVar(var_name)

        # Constraint 1: Each course must be scheduled exactly once for each group
        for group_id in self.group_ids:
            group_courses = self.groups[group_id]['courses']
            for course_id in group_courses:
                if course_id not in assignments[group_id]:
                    continue

                course_vars = []
                for timeslot_id in self.timeslot_ids:
                    if timeslot_id in assignments[group_id][course_id]:
                        for teacher_id in assignments[group_id][course_id][timeslot_id]:
                            for room_id in assignments[group_id][course_id][timeslot_id][teacher_id]:
                                course_vars.append(assignments[group_id][course_id][timeslot_id][teacher_id][room_id])

                if course_vars:
                    model.Add(sum(course_vars) == 1)

        # Constraint 2: No teacher conflicts
        for teacher_id in self.teacher_ids:
            for timeslot_id in self.timeslot_ids:
                teacher_vars = []
                for group_id in self.group_ids:
                    group_courses = self.groups[group_id]['courses']
                    for course_id in group_courses:
                        if (course_id in assignments[group_id] and 
                            timeslot_id in assignments[group_id][course_id] and
                            teacher_id in assignments[group_id][course_id][timeslot_id]):
                            for room_id in assignments[group_id][course_id][timeslot_id][teacher_id]:
                                teacher_vars.append(assignments[group_id][course_id][timeslot_id][teacher_id][room_id])

                if teacher_vars:
                    model.Add(sum(teacher_vars) <= 1)

        # Constraint 3: No room conflicts
        for room_id in self.room_ids:
            for timeslot_id in self.timeslot_ids:
                room_vars = []
                for group_id in self.group_ids:
                    group_courses = self.groups[group_id]['courses']
                    for course_id in group_courses:
                        if (course_id in assignments[group_id] and 
                            timeslot_id in assignments[group_id][course_id]):
                            for teacher_id in assignments[group_id][course_id][timeslot_id]:
                                if room_id in assignments[group_id][course_id][timeslot_id][teacher_id]:
                                    room_vars.append(assignments[group_id][course_id][timeslot_id][teacher_id][room_id])

                if room_vars:
                    model.Add(sum(room_vars) <= 1)

        # Constraint 4: No group conflicts (student groups can't have overlapping classes)
        for group_id in self.group_ids:
            for timeslot_id in self.timeslot_ids:
                group_vars = []
                group_courses = self.groups[group_id]['courses']
                for course_id in group_courses:
                    if (course_id in assignments[group_id] and 
                        timeslot_id in assignments[group_id][course_id]):
                        for teacher_id in assignments[group_id][course_id][timeslot_id]:
                            for room_id in assignments[group_id][course_id][timeslot_id][teacher_id]:
                                group_vars.append(assignments[group_id][course_id][timeslot_id][teacher_id][room_id])

                if group_vars:
                    model.Add(sum(group_vars) <= 1)

        # Solve the model
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0
        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            logger.info("Found feasible solution with OR-Tools")

            # Extract solution
            schedule = {}
            for group_id in self.group_ids:
                schedule[group_id] = {}
                group_courses = self.groups[group_id]['courses']

                for course_id in group_courses:
                    if course_id not in assignments[group_id]:
                        continue

                    for timeslot_id in self.timeslot_ids:
                        if timeslot_id in assignments[group_id][course_id]:
                            for teacher_id in assignments[group_id][course_id][timeslot_id]:
                                for room_id in assignments[group_id][course_id][timeslot_id][teacher_id]:
                                    var = assignments[group_id][course_id][timeslot_id][teacher_id][room_id]
                                    if solver.Value(var) == 1:
                                        schedule[group_id][course_id] = {
                                            'timeslot': timeslot_id,
                                            'teacher': teacher_id,
                                            'room': room_id
                                        }

            return schedule
        else:
            logger.error(f"OR-Tools solver failed with status: {status}")
            return None

    def _get_suitable_rooms(self, course_type: str) -> List[str]:
        """Get rooms suitable for course type"""
        suitable_rooms = []

        for room_id, room_data in self.rooms.items():
            room_type = room_data['type'].lower()

            if course_type == 'LAB' and 'lab' in room_type:
                suitable_rooms.append(room_id)
            elif course_type == 'PROJECT' and 'project' in room_type:
                suitable_rooms.append(room_id)
            elif course_type in ['TH', 'PR'] and 'classroom' in room_type:
                suitable_rooms.append(room_id)
            # Fallback: any room can be used if specific type not available
            elif len(suitable_rooms) == 0:
                suitable_rooms.append(room_id)

        return suitable_rooms if suitable_rooms else list(self.room_ids)

    def _optimize_schedule(self, base_schedule: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize schedule using DEAP genetic algorithm"""
        logger.info("Optimizing schedule with genetic algorithm...")

        # Set up DEAP
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)

        toolbox = base.Toolbox()

        # Generate initial population based on base schedule
        def create_individual():
            return self._schedule_to_individual(base_schedule)

        toolbox.register("individual", tools.initIterate, creator.Individual, create_individual)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)
        toolbox.register("evaluate", self._evaluate_schedule)
        toolbox.register("mate", self._crossover)
        toolbox.register("mutate", self._mutate)
        toolbox.register("select", tools.selTournament, tournsize=3)

        # Evolution parameters
        population_size = 20
        generations = 10
        cx_prob = 0.7
        mut_prob = 0.2

        # Create initial population
        population = toolbox.population(n=population_size)

        # Evaluate initial population
        fitnesses = list(map(toolbox.evaluate, population))
        for ind, fit in zip(population, fitnesses):
            ind.fitness.values = fit

        # Evolution loop
        for generation in range(generations):
            # Selection
            offspring = toolbox.select(population, len(population))
            offspring = list(map(toolbox.clone, offspring))

            # Crossover and mutation
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < cx_prob:
                    toolbox.mate(child1, child2)
                    del child1.fitness.values
                    del child2.fitness.values

            for mutant in offspring:
                if random.random() < mut_prob:
                    toolbox.mutate(mutant)
                    del mutant.fitness.values

            # Evaluate invalid individuals
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = map(toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit

            population[:] = offspring

            # Log progress
            fits = [ind.fitness.values[0] for ind in population]
            logger.info(f"Generation {generation + 1}: Best={max(fits):.2f}, Avg={np.mean(fits):.2f}")

        # Return best solution
        best_individual = tools.selBest(population, 1)[0]
        optimized_schedule = self._individual_to_schedule(best_individual)

        return optimized_schedule

    def _schedule_to_individual(self, schedule: Dict[str, Any]) -> List:
        """Convert schedule to individual representation for GA"""
        individual = []

        for group_id in sorted(self.group_ids):
            if group_id in schedule:
                group_courses = self.groups[group_id]['courses']
                for course_id in sorted(group_courses):
                    if course_id in schedule[group_id]:
                        assignment = schedule[group_id][course_id]
                        individual.extend([
                            self.timeslot_ids.index(assignment['timeslot']),
                            self.teacher_ids.index(assignment['teacher']),
                            self.room_ids.index(assignment['room'])
                        ])
                    else:
                        individual.extend([0, 0, 0])  # Default values

        return individual

    def _individual_to_schedule(self, individual: List) -> Dict[str, Any]:
        """Convert individual representation back to schedule"""
        schedule = {}
        idx = 0

        for group_id in sorted(self.group_ids):
            schedule[group_id] = {}
            group_courses = self.groups[group_id]['courses']

            for course_id in sorted(group_courses):
                if course_id in self.course_ids and idx + 2 < len(individual):
                    timeslot_idx = individual[idx] % len(self.timeslot_ids)
                    teacher_idx = individual[idx + 1] % len(self.teacher_ids)
                    room_idx = individual[idx + 2] % len(self.room_ids)

                    schedule[group_id][course_id] = {
                        'timeslot': self.timeslot_ids[timeslot_idx],
                        'teacher': self.teacher_ids[teacher_idx],
                        'room': self.room_ids[room_idx]
                    }

                idx += 3

        return schedule

    def _evaluate_schedule(self, individual: List) -> Tuple[float]:
        """Evaluate schedule fitness based on soft constraints"""
        schedule = self._individual_to_schedule(individual)

        score = 0.0

        # Soft constraint 1: Minimize gaps in schedules
        score += self._evaluate_gaps(schedule) * 0.3

        # Soft constraint 2: Spread subjects evenly across the week
        score += self._evaluate_distribution(schedule) * 0.3

        # Soft constraint 3: Balance faculty workload
        score += self._evaluate_workload_balance(schedule) * 0.4

        return (score,)

    def _evaluate_gaps(self, schedule: Dict[str, Any]) -> float:
        """Evaluate gaps in student and teacher schedules"""
        total_gap_penalty = 0

        # Calculate gaps for each group
        for group_id in self.group_ids:
            if group_id not in schedule:
                continue

            # Get timeslots for this group
            group_timeslots = []
            for course_id in schedule[group_id]:
                timeslot_id = schedule[group_id][course_id]['timeslot']
                slot_index = self.timeslots[timeslot_id]['slot_index']
                group_timeslots.append(slot_index)

            # Calculate gaps
            if len(group_timeslots) > 1:
                group_timeslots.sort()
                gaps = 0
                for i in range(1, len(group_timeslots)):
                    gap = group_timeslots[i] - group_timeslots[i-1] - 1
                    gaps += max(0, gap)

                total_gap_penalty += gaps

        # Lower penalty means better score
        return max(0, 100 - total_gap_penalty * 5)

    def _evaluate_distribution(self, schedule: Dict[str, Any]) -> float:
        """Evaluate distribution of subjects across the week"""
        day_distribution = {}
        total_classes = 0

        for group_id in schedule:
            for course_id in schedule[group_id]:
                timeslot_id = schedule[group_id][course_id]['timeslot']
                day = self.timeslots[timeslot_id]['day']

                day_distribution[day] = day_distribution.get(day, 0) + 1
                total_classes += 1

        if total_classes == 0:
            return 0

        # Calculate ideal distribution
        days = list(set(self.timeslots[ts]['day'] for ts in self.timeslot_ids))
        ideal_per_day = total_classes / len(days)

        # Calculate deviation from ideal
        deviation = 0
        for day in days:
            actual = day_distribution.get(day, 0)
            deviation += abs(actual - ideal_per_day)

        # Lower deviation means better score
        return max(0, 100 - deviation * 10)

    def _evaluate_workload_balance(self, schedule: Dict[str, Any]) -> float:
        """Evaluate balance in teacher workloads"""
        teacher_workload = {}

        for group_id in schedule:
            for course_id in schedule[group_id]:
                teacher_id = schedule[group_id][course_id]['teacher']
                teacher_workload[teacher_id] = teacher_workload.get(teacher_id, 0) + 1

        if not teacher_workload:
            return 0

        workloads = list(teacher_workload.values())
        avg_workload = sum(workloads) / len(workloads)

        # Calculate deviation from average
        deviation = sum(abs(w - avg_workload) for w in workloads)

        # Lower deviation means better balance
        return max(0, 100 - deviation * 5)

    def _crossover(self, ind1, ind2):
        """Crossover operation for genetic algorithm"""
        if len(ind1) != len(ind2):
            return ind1, ind2

        # Single point crossover
        if len(ind1) > 3:
            cx_point = random.randint(1, len(ind1) - 1)
            cx_point = (cx_point // 3) * 3  # Align to course boundaries

            temp = ind1[cx_point:]
            ind1[cx_point:] = ind2[cx_point:]
            ind2[cx_point:] = temp

        return ind1, ind2

    def _mutate(self, individual):
        """Mutation operation for genetic algorithm"""
        if len(individual) >= 3:
            # Randomly select a course assignment to mutate
            mutation_point = random.randint(0, (len(individual) // 3) - 1) * 3

            # Mutate timeslot, teacher, or room
            component = random.randint(0, 2)
            if component == 0:  # Timeslot
                individual[mutation_point] = random.randint(0, len(self.timeslot_ids) - 1)
            elif component == 1:  # Teacher
                individual[mutation_point + 1] = random.randint(0, len(self.teacher_ids) - 1)
            else:  # Room
                individual[mutation_point + 2] = random.randint(0, len(self.room_ids) - 1)

        return (individual,)

def test_scheduler():
    """Test the scheduler with sample data"""
    from input_parser import create_sample_data, InputParser

    # Create sample data
    create_sample_data()

    # Parse the data
    parser = InputParser('sample_input.xlsx')
    courses, teachers, rooms, timeslots, groups = parser.parse_excel()

    # Validate data
    errors = parser.validate_data()
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
        return

    # Create scheduler and generate timetable
    scheduler = TimetableScheduler(courses, teachers, rooms, timeslots, groups)
    schedule = scheduler.generate_schedule()

    if schedule:
        print("Timetable generated successfully!")
        print("Sample assignments:")
        for group_id in list(schedule.keys())[:2]:  # Show first 2 groups
            print(f"\nGroup {group_id}:")
            for course_id in schedule[group_id]:
                assignment = schedule[group_id][course_id]
                timeslot = timeslots[assignment['timeslot']]
                print(f"  {course_id}: {timeslot['day']} {timeslot['time']} - "
                      f"Teacher: {assignment['teacher']} - Room: {assignment['room']}")
    else:
        print("Failed to generate timetable")

if __name__ == "__main__":
    test_scheduler()
