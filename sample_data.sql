delete from timetables;
delete from subjects;
delete from teachers;
delete from rooms;
delete from classes;

insert into classes (name) values
('CSE-A'),
('CSE-B'),
('CSE-C'),
('IT-A'),
('ECE-A')
on conflict (name) do nothing;

insert into teachers (name, subjects) values
('Dr Sharma', 'Python Programming, Data Structures, Design and Analysis of Algorithms'),
('Prof Khan', 'Artificial Intelligence, Machine Learning'),
('Ms Reddy', 'Database Management Systems, Web Technologies'),
('Mr Joseph', 'Operating Systems, Computer Networks, Computer Organization'),
('Dr Mehta', 'Cloud Computing, Cyber Security, Software Engineering'),
('Ms Iyer', 'Statistics, Discrete Mathematics');

insert into rooms (name) values
('Room 101'),
('Room 102'),
('Room 103'),
('Lab 1'),
('Lab 2')
on conflict (name) do nothing;
