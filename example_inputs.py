# Testing Daily Shifts
example_1 = """
The database team will start their on call rotation on Jan 1, 2025. This group is
on call Thurs 9am-12pm, Friday 9am-12pm, Nairobi timezone. Users will rotate
each day in the following order: Pam Beesly, Dwight Shrute, Dwight Shrute, Pam
Beesly, Creed Braton, Creed Braton.
"""

example_2 = """
The devops group will start their on call rotation on Jan 1, 2025. This group is
on call Mon 12pm-5pm, Tues 12pm-5pm, and Wed 12pm-5pm, Nairobi timezone.
Users will rotate each day in the following order: Saul Goodman, Jesse Pinkman,
Kim Wexler.
"""

# Testing Weekly Shifts
example_3 = """
The helpdesk team will start their on call rotation on Jan 4, 2025. This group is
on call Thurs 9am-12pm, Friday 9am-12pm, Kolkata timezone. Users will rotate
each week in the following order: Kelly Kapoor, Bob Vance, Bob Vance, Kelly
Kapoor, Toby Flenderson, Toby Flenderson.
"""

example_4 = """
The legal team will start their on call rotation on Jan 4, 2025. This group is on
call Mon 12pm-5pm, Tues 12pm-5pm, and Wed 12pm-5pm, Kolkata timezone. Users
will rotate each week in the following order: Wendy Byrde, Darlene Snell, Ruth
Langmore.
"""

# Testing adding multiple shifts in a day - daily
example_7 = """
The marketing group will start their on call rotation on Jan 6, 2025. This group
is on call Mon 12pm-5pm, Sat 12pm-5pm, and Sun 12pm-5pm, Los Angeles timezone.
Users will rotate each day in the following order: Saul Goodman, Jesse Pinkman,
Kim Wexler.
"""

example_8 = """
The Research & Development group will start their on call rotation on Jan 6, 2025.
This group is on call Fri 9am-5pm, Sat 9am-5pm, and Sun 9am-5pm, Los Angeles timezone.
Users will rotate each day in the following order: Green Lantern, The Flash.
"""

# Testing adding multiple shifts in a day - weekly
example_5 = """
The finance team will start their on call rotation on Jan 5, 2025. This group is
on call Thurs 9am-12pm, Friday 9am-12pm, Tokyo timezone. Users will rotate
each week in the following order: Gus Fring, Tuco Salamanca.
"""

example_6 = """
The HR team will start their oncall rotation on Jan 5, 2025. This
group is on call Thurs 12pm-5pm, Friday 12pm-5pm, Tokyo timezone. Users
will rotate each week in the following order: Anakin, Grogu, Chewbacca.
"""

# Testing every x number of days
example_9 = """
The UX team starts their on call rotation on Jan 3, 2025. This team is on call
Tue 9am-5pm, Wed 9am-5pm, and Thurs 9am-5pm, New York timezone. Users will rotate
every three days in the following order: Gandalf, Frodo, Bilbo, Gimli.
"""

example_10 = """
The engineering team will start their on call rotation on Jan 3, 2025. This team
is on call Fri 9am-5pm, Sat 9am-5pm, and Sun 9am-5pm, New York timezone. Users
will rotate every four days in the following order: Nemo, Dori.
"""

# Testing every x number of weeks
example_11 = """
The sales team will start their on call rotation on Jan 4, 2025. This team
is on call Sat 9am-5pm, Sun 9am-5pm, and Mon 9am-5pm, Denver timezone. Users
will rotate every 2 weeks in the following order: Sailor Mercury, Sailor Mars,
Sailor Jupiter.
"""

example_12 = """
The support team will start their on call rotation on Jan 4, 2025. This team
is on call Tue 9am-5pm, Wed 9am-5pm, and Thur 9am-5pm, Denver timezone. Users
will rotate every 3 weeks in the following order: Sailor Moon, Sailor Venus.
"""

# Testing one person on call everday
example_13 = """
Buzz Lightyear starts their on call rotation on Jan 1, 2025.
They are on call 9am-12pm everyday, Sao Paulo timezone.
"""

example_14 = """
Mulan starts their on call rotation on Jan 2, 2025.
They are on call 12pm-5pm everyday, Sao Paulo timezone.
"""

# Testing multiple people on call everyday

# Testing daily shifts spanning multiple days

# Testing weekly shifts spanning multiple days

# Testing daily handoff

# Testing weekly handoff

# Testing Overlapping Shifts

# Testing missing input
