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

        # Ordered days for scheduling
        self.days = sorted(set(ts['day'] for ts in timeslots.values()))

        # Course type frequency mapping
        self.course_type_frequency = {
            'TH': 3,  # Theory courses 3 times per week
            'LAB': 2,  # Lab courses 2 times per week
            'PROJECT': 1,  # Project courses 1 time per week
            'PR': 1  # Practical courses 1 time per week
        }

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
        assignments = {}

        # Create variables for each possible assignment
        for group_id in self.group_ids:
            assignments[group_id] = {}
            group_courses = self.groups[group_id]['courses']

            for course_id in group_courses:
                if course_id not in self.course_ids:
                    continue
                course_type = self.courses[course_id]['type']
                frequency = self.course_type_frequency.get(course_type, 1)
                course_duration = self.courses[course_id]['duration']

                # Create multiple instances based on frequency
                for instance in range(1, frequency + 1):
                    instance_key = f"{course_id}_{instance}"
                    assignments[group_id][instance_key] = {}
                    suitable_teachers = [t for t in self.teacher_ids 
                                       if course_id in self.teachers[t]['courses_handled']]
                    suitable_rooms = self._get_suitable_rooms(course_type)

                    # Group timeslots by day
                    day_to_slots = {}
                    for ts_id in self.timeslot_ids:
                        day = self.timeslots[ts_id]['day']
                        if day not in day_to_slots:
                            day_to_slots[day] = []
                        day_to_slots[day].append(ts_id)

                    for day in day_to_slots:
                        day_slots = sorted(day_to_slots[day], key=lambda x: self.timeslots[x]['slot_index'])
                        for i in range(len(day_slots) - course_duration + 1):
                            timeslot_group = day_slots[i:i + course_duration]
                            if len(timeslot_group) == course_duration:
                                timeslot_group_id = '_'.join(timeslot_group)
                                assignments[group_id][instance_key][timeslot_group_id] = {}
                                for teacher_id in suitable_teachers:
                                    assignments[group_id][instance_key][timeslot_group_id][teacher_id] = {}
                                    for room_id in suitable_rooms:
                                        var_name = f"{group_id}_{instance_key}_{timeslot_group_id}_{teacher_id}_{room_id}"
                                        assignments[group_id][instance_key][timeslot_group_id][teacher_id][room_id] = \
                                            model.NewBoolVar(var_name)

        # Constraint 1: Each course instance must be scheduled exactly once
        for group_id in self.group_ids:
            for instance_key in assignments[group_id]:
                course_vars = []
                for timeslot_group_id in assignments[group_id][instance_key]:
                    for teacher_id in assignments[group_id][instance_key][timeslot_group_id]:
                        for room_id in assignments[group_id][instance_key][timeslot_group_id][teacher_id]:
                            course_vars.append(assignments[group_id][instance_key][timeslot_group_id][teacher_id][room_id])
                if course_vars:
                    model.Add(sum(course_vars) == 1)

        # Constraint 2: No teacher conflicts across consecutive timeslots
        for teacher_id in self.teacher_ids:
            for day in self.days:
                day_slots = [ts_id for ts_id in self.timeslot_ids if self.timeslots[ts_id]['day'] == day]
                day_slots.sort(key=lambda x: self.timeslots[x]['slot_index'])
                for i in range(len(day_slots)):
                    teacher_vars = []
                    for group_id in self.group_ids:
                        for instance_key in assignments[group_id]:
                            for timeslot_group_id in assignments[group_id][instance_key]:
                                timeslots = timeslot_group_id.split('_')
                                if day_slots[i] in timeslots:
                                    for teacher_id_key in assignments[group_id][instance_key][timeslot_group_id]:
                                        if teacher_id_key == teacher_id:
                                            for room_id in assignments[group_id][instance_key][timeslot_group_id][teacher_id]:
                                                teacher_vars.append(
                                                    assignments[group_id][instance_key][timeslot_group_id][teacher_id][room_id]
                                                )
                    if teacher_vars:
                        model.Add(sum(teacher_vars) <= 1)

        # Constraint 3: No room conflicts across consecutive timeslots
        for room_id in self.room_ids:
            for day in self.days:
                day_slots = [ts_id for ts_id in self.timeslot_ids if self.timeslots[ts_id]['day'] == day]
                day_slots.sort(key=lambda x: self.timeslots[x]['slot_index'])
                for i in range(len(day_slots)):
                    room_vars = []
                    for group_id in self.group_ids:
                        for instance_key in assignments[group_id]:
                            for timeslot_group_id in assignments[group_id][instance_key]:
                                timeslots = timeslot_group_id.split('_')
                                if day_slots[i] in timeslots:
                                    for teacher_id in assignments[group_id][instance_key][timeslot_group_id]:
                                        if room_id in assignments[group_id][instance_key][timeslot_group_id][teacher_id]:
                                            room_vars.append(
                                                assignments[group_id][instance_key][timeslot_group_id][teacher_id][room_id]
                                            )
                    if room_vars:
                        model.Add(sum(room_vars) <= 1)

        # Constraint 4: No group conflicts across consecutive timeslots
        for group_id in self.group_ids:
            for day in self.days:
                day_slots = [ts_id for ts_id in self.timeslot_ids if self.timeslots[ts_id]['day'] == day]
                day_slots.sort(key=lambda x: self.timeslots[x]['slot_index'])
                for i in range(len(day_slots)):
                    group_vars = []
                    for instance_key in assignments[group_id]:
                        for timeslot_group_id in assignments[group_id][instance_key]:
                            timeslots = timeslot_group_id.split('_')
                            if day_slots[i] in timeslots:
                                for teacher_id in assignments[group_id][instance_key][timeslot_group_id]:
                                    for room_id in assignments[group_id][instance_key][timeslot_group_id][teacher_id]:
                                        group_vars.append(
                                            assignments[group_id][instance_key][timeslot_group_id][teacher_id][room_id]
                                        )
                    if group_vars:
                        model.Add(sum(group_vars) <= 1)

        # Constraint 5: Ensure different days for multiple instances of the same course
        for group_id in self.group_ids:
            group_courses = self.groups[group_id]['courses']
            for course_id in group_courses:
                if course_id not in self.course_ids:
                    continue
                course_type = self.courses[course_id]['type']
                frequency = self.course_type_frequency.get(course_type, 1)
                if frequency > 1:
                    instance_keys = [f"{course_id}_{i}" for i in range(1, frequency + 1)]
                    for i, instance_key_i in enumerate(instance_keys[:-1]):
                        for instance_key_j in instance_keys[i + 1:]:
                            for timeslot_group_i in assignments[group_id].get(instance_key_i, {}):
                                day_i = self.timeslots[timeslot_group_i.split('_')[0]]['day']
                                for timeslot_group_j in assignments[group_id].get(instance_key_j, {}):
                                    day_j = self.timeslots[timeslot_group_j.split('_')[0]]['day']
                                    if day_i == day_j:
                                        for teacher_id_i in assignments[group_id][instance_key_i][timeslot_group_i]:
                                            for room_id_i in assignments[group_id][instance_key_i][timeslot_group_i][teacher_id_i]:
                                                for teacher_id_j in assignments[group_id][instance_key_j][timeslot_group_j]:
                                                    for room_id_j in assignments[group_id][instance_key_j][timeslot_group_j][teacher_id_j]:
                                                        model.Add(
                                                            assignments[group_id][instance_key_i][timeslot_group_i][teacher_id_i][room_id_i] +
                                                            assignments[group_id][instance_key_j][timeslot_group_j][teacher_id_j][room_id_j] <= 1
                                                        )

        # Solve the model
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 120.0  # Increased time for complex constraints
        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            logger.info("Found feasible solution with OR-Tools")
            schedule = {}
            for group_id in self.group_ids:
                schedule[group_id] = {}
                for instance_key in assignments[group_id]:
                    course_id = instance_key.split('_')[0]  # Extract original course_id
                    course_duration = self.courses[course_id]['duration']
                    for timeslot_group_id in assignments[group_id][instance_key]:
                        for teacher_id in assignments[group_id][instance_key][timeslot_group_id]:
                            for room_id in assignments[group_id][instance_key][timeslot_group_id][teacher_id]:
                                var = assignments[group_id][instance_key][timeslot_group_id][teacher_id][room_id]
                                if solver.Value(var) == 1:
                                    timeslots = timeslot_group_id.split('_')
                                    for i, ts_id in enumerate(timeslots):
                                        schedule_key = f"{instance_key}_part{i+1}" if course_duration > 1 else instance_key
                                        schedule[group_id][schedule_key] = {
                                            'timeslot': ts_id,
                                            'teacher': teacher_id,
                                            'room': room_id,
                                            'course_id': course_id
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
            elif len(suitable_rooms) == 0:
                suitable_rooms.append(room_id)
        return suitable_rooms if suitable_rooms else list(self.room_ids)

    def _optimize_schedule(self, base_schedule: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize schedule using DEAP genetic algorithm"""
        logger.info("Optimizing schedule with genetic algorithm...")
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)
        toolbox = base.Toolbox()

        def create_individual():
            return self._schedule_to_individual(base_schedule)

        toolbox.register("individual", tools.initIterate, creator.Individual, create_individual)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)
        toolbox.register("evaluate", self._evaluate_schedule)
        toolbox.register("mate", self._crossover)
        toolbox.register("mutate", self._mutate)
        toolbox.register("select", tools.selTournament, tournsize=3)

        population_size = 20
        generations = 10
        cx_prob = 0.7
        mut_prob = 0.2

        population = toolbox.population(n=population_size)
        fitnesses = list(map(toolbox.evaluate, population))
        for ind, fit in zip(population, fitnesses):
            ind.fitness.values = fit

        for generation in range(generations):
            offspring = toolbox.select(population, len(population))
            offspring = list(map(toolbox.clone, offspring))
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < cx_prob:
                    toolbox.mate(child1, child2)
                    del child1.fitness.values
                    del child2.fitness.values
            for mutant in offspring:
                if random.random() < mut_prob:
                    toolbox.mutate(mutant)
                    del mutant.fitness.values
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = map(toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit
            population[:] = offspring
            fits = [ind.fitness.values[0] for ind in population]
            logger.info(f"Generation {generation + 1}: Best={max(fits):.2f}, Avg={np.mean(fits):.2f}")

        best_individual = tools.selBest(population, 1)[0]
        optimized_schedule = self._individual_to_schedule(best_individual)
        return optimized_schedule

    def _schedule_to_individual(self, schedule: Dict[str, Any]) -> List:
        """Convert schedule to individual representation for GA"""
        individual = []
        for group_id in sorted(self.group_ids):
            if group_id in schedule:
                group_courses = set(assignment['course_id'] for assignment in schedule[group_id].values())
                for course_id in sorted(group_courses):
                    frequency = self.course_type_frequency.get(self.courses[course_id]['type'], 1)
                    for instance in range(1, frequency + 1):
                        instance_key = f"{course_id}_{instance}"
                        assignments = [a for a in schedule[group_id].items() if a[0].startswith(instance_key)]
                        if assignments:
                            first_assignment = assignments[0][1]
                            individual.extend([
                                self.timeslot_ids.index(first_assignment['timeslot']),
                                self.teacher_ids.index(first_assignment['teacher']),
                                self.room_ids.index(first_assignment['room'])
                            ])
                        else:
                            individual.extend([0, 0, 0])
        return individual

    def _individual_to_schedule(self, individual: List) -> Dict[str, Any]:
        """Convert individual representation back to schedule"""
        schedule = {}
        idx = 0
        for group_id in sorted(self.group_ids):
            schedule[group_id] = {}
            group_courses = self.groups[group_id]['courses']
            for course_id in sorted(group_courses):
                if course_id not in self.course_ids:
                    continue
                course_type = self.courses[course_id]['type']
                frequency = self.course_type_frequency.get(course_type, 1)
                course_duration = self.courses[course_id]['duration']
                for instance in range(1, frequency + 1):
                    instance_key = f"{course_id}_{instance}"
                    if idx + 2 < len(individual):
                        timeslot_idx = individual[idx] % len(self.timeslot_ids)
                        teacher_idx = individual[idx + 1] % len(self.teacher_ids)
                        room_idx = individual[idx + 2] % len(self.room_ids)
                        timeslot_id = self.timeslot_ids[timeslot_idx]
                        day = self.timeslots[timeslot_id]['day']
                        slot_index = self.timeslots[timeslot_id]['slot_index']
                        day_slots = sorted(
                            [ts for ts in self.timeslot_ids if self.timeslots[ts]['day'] == day],
                            key=lambda x: self.timeslots[x]['slot_index']
                        )
                        start_idx = day_slots.index(timeslot_id)
                        if start_idx + course_duration - 1 < len(day_slots):
                            timeslots = day_slots[start_idx:start_idx + course_duration]
                            for i, ts_id in enumerate(timeslots):
                                schedule_key = f"{instance_key}_part{i+1}" if course_duration > 1 else instance_key
                                schedule[group_id][schedule_key] = {
                                    'timeslot': ts_id,
                                    'teacher': self.teacher_ids[teacher_idx],
                                    'room': self.room_ids[room_idx],
                                    'course_id': course_id
                                }
                        idx += 3
        return schedule

    def _evaluate_schedule(self, individual: List) -> Tuple[float]:
        """Evaluate schedule fitness based on soft constraints"""
        schedule = self._individual_to_schedule(individual)
        score = 0.0
        score += self._evaluate_gaps(schedule) * 0.3
        score += self._evaluate_distribution(schedule) * 0.3
        score += self._evaluate_workload_balance(schedule) * 0.4
        return (score,)

    def _evaluate_gaps(self, schedule: Dict[str, Any]) -> float:
        """Evaluate gaps in student and teacher schedules"""
        total_gap_penalty = 0
        for group_id in self.group_ids:
            if group_id not in schedule:
                continue
            group_timeslots = []
            for assignment in schedule[group_id].values():
                timeslot_id = assignment['timeslot']
                slot_index = self.timeslots[timeslot_id]['slot_index']
                group_timeslots.append(slot_index)
            if len(group_timeslots) > 1:
                group_timeslots.sort()
                gaps = 0
                for i in range(1, len(group_timeslots)):
                    gap = group_timeslots[i] - group_timeslots[i-1] - 1
                    gaps += max(0, gap)
                total_gap_penalty += gaps
        return max(0, 100 - total_gap_penalty * 5)

    def _evaluate_distribution(self, schedule: Dict[str, Any]) -> float:
        """Evaluate distribution of subjects across the week"""
        day_distribution = {}
        total_classes = 0
        for group_id in schedule:
            for assignment in schedule[group_id].values():
                timeslot_id = assignment['timeslot']
                day = self.timeslots[timeslot_id]['day']
                day_distribution[day] = day_distribution.get(day, 0) + 1
                total_classes += 1
        if total_classes == 0:
            return 0
        days = list(set(self.timeslots[ts]['day'] for ts in self.timeslot_ids))
        ideal_per_day = total_classes / len(days)
        deviation = 0
        for day in days:
            actual = day_distribution.get(day, 0)
            deviation += abs(actual - ideal_per_day)
        return max(0, 100 - deviation * 10)

    def _evaluate_workload_balance(self, schedule: Dict[str, Any]) -> float:
        """Evaluate balance in teacher workloads"""
        teacher_workload = {}
        for group_id in schedule:
            for assignment in schedule[group_id].values():
                teacher_id = assignment['teacher']
                teacher_workload[teacher_id] = teacher_workload.get(teacher_id, 0) + 1
        if not teacher_workload:
            return 0
        workloads = list(teacher_workload.values())
        avg_workload = sum(workloads) / len(workloads)
        deviation = sum(abs(w - avg_workload) for w in workloads)
        return max(0, 100 - deviation * 5)

    def _crossover(self, ind1, ind2):
        """Crossover operation for genetic algorithm"""
        if len(ind1) != len(ind2):
            return ind1, ind2
        if len(ind1) > 3:
            cx_point = random.randint(1, len(ind1) - 1)
            cx_point = (cx_point // 3) * 3
            temp = ind1[cx_point:]
            ind1[cx_point:] = ind2[cx_point:]
            ind2[cx_point:] = temp
        return ind1, ind2

    def _mutate(self, individual):
        """Mutation operation for genetic algorithm"""
        if len(individual) >= 3:
            mutation_point = random.randint(0, (len(individual) // 3) - 1) * 3
            component = random.randint(0, 2)
            if component == 0:
                individual[mutation_point] = random.randint(0, len(self.timeslot_ids) - 1)
            elif component == 1:
                individual[mutation_point + 1] = random.randint(0, len(self.teacher_ids) - 1)
            else:
                individual[mutation_point + 2] = random.randint(0, len(self.room_ids) - 1)
        return (individual,)

def test_scheduler():
    """Test the scheduler with sample data"""
    from input_parser import create_sample_data, InputParser
    create_sample_data()
    parser = InputParser('sample_input.xlsx')
    courses, teachers, rooms, timeslots, groups = parser.parse_excel()
    errors = parser.validate_data()
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
        return
    scheduler = TimetableScheduler(courses, teachers, rooms, timeslots, groups)
    schedule = scheduler.generate_schedule()
    if schedule:
        print("Timetable generated successfully!")
        print("Sample assignments:")
        for group_id in list(schedule.keys())[:2]:
            print(f"\nGroup {group_id}:")
            for course_key, assignment in schedule[group_id].items():
                timeslot = timeslots[assignment['timeslot']]
                print(f"  {course_key}: {timeslot['day']} {timeslot['time']} - "
                      f"Teacher: {assignment['teacher']} - Room: {assignment['room']}")
    else:
        print("Failed to generate timetable")

if __name__ == "__main__":
    test_scheduler()
