-- ============================================================
-- COLLEGE PROJECT TEAM FINDER
-- DBMS OPEN ENDED PROJECT
-- MYSQL DATABASE + 70 SQL QUERIES
-- ============================================================


-- ============================================================
-- PART A : DATABASE CREATION
-- ============================================================

DROP DATABASE IF EXISTS college_team_finder;

CREATE DATABASE college_team_finder;

USE college_team_finder;


-- ============================================================
-- TABLE 1 : DEPARTMENTS
-- ============================================================

CREATE TABLE departments (
    department_id INT AUTO_INCREMENT PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL UNIQUE,
    department_code VARCHAR(20) NOT NULL UNIQUE
);


-- ============================================================
-- TABLE 2 : STUDENTS
-- ============================================================

CREATE TABLE students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    department_id INT NOT NULL,
    year_of_study INT NOT NULL,
    college VARCHAR(150),
    bio TEXT,
    github_portfolio VARCHAR(255),

    experience_level ENUM(
        'BEGINNER',
        'INTERMEDIATE',
        'ADVANCED',
        'EXPERT'
    ) DEFAULT 'BEGINNER',

    availability_status ENUM(
        'AVAILABLE',
        'PARTIALLY_AVAILABLE',
        'NOT_AVAILABLE'
    ) DEFAULT 'AVAILABLE',

    profile_photo VARCHAR(255),

    account_status ENUM(
        'ACTIVE',
        'BLOCKED',
        'SUSPENDED'
    ) DEFAULT 'ACTIVE',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);


-- ============================================================
-- TABLE 3 : SKILLS
-- ============================================================

CREATE TABLE skills (
    skill_id INT AUTO_INCREMENT PRIMARY KEY,
    skill_name VARCHAR(100) NOT NULL UNIQUE,
    skill_category VARCHAR(100),
    description TEXT
);


-- ============================================================
-- TABLE 4 : STUDENT_SKILLS
-- ============================================================

CREATE TABLE student_skills (
    student_skill_id INT AUTO_INCREMENT PRIMARY KEY,

    student_id INT NOT NULL,
    skill_id INT NOT NULL,

    proficiency_level ENUM(
        'BEGINNER',
        'INTERMEDIATE',
        'ADVANCED',
        'EXPERT'
    ) DEFAULT 'BEGINNER',

    years_of_experience DECIMAL(3,1) DEFAULT 0.0,

    is_verified BOOLEAN DEFAULT FALSE,

    FOREIGN KEY (student_id)
        REFERENCES students(student_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    FOREIGN KEY (skill_id)
        REFERENCES skills(skill_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    UNIQUE(student_id, skill_id)
);


-- ============================================================
-- TABLE 5 : PROJECTS
-- ============================================================

CREATE TABLE projects (
    project_id INT AUTO_INCREMENT PRIMARY KEY,

    created_by INT NOT NULL,

    project_title VARCHAR(200) NOT NULL,

    project_description TEXT NOT NULL,

    domain VARCHAR(100) NOT NULL,

    max_team_size INT NOT NULL,

    current_team_size INT DEFAULT 1,

    difficulty_level ENUM(
        'EASY',
        'MEDIUM',
        'HARD'
    ) DEFAULT 'MEDIUM',

    deadline DATE,

    project_status ENUM(
        'OPEN',
        'FULL',
        'IN_PROGRESS',
        'COMPLETED',
        'CANCELLED'
    ) DEFAULT 'OPEN',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (created_by)
        REFERENCES students(student_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CHECK(max_team_size > 0),
    CHECK(current_team_size >= 0)
);


-- ============================================================
-- TABLE 6 : PROJECT_REQUIRED_SKILLS
-- ============================================================

CREATE TABLE project_required_skills (
    project_skill_id INT AUTO_INCREMENT PRIMARY KEY,

    project_id INT NOT NULL,
    skill_id INT NOT NULL,

    importance_weight INT DEFAULT 5,

    minimum_proficiency ENUM(
        'BEGINNER',
        'INTERMEDIATE',
        'ADVANCED',
        'EXPERT'
    ) DEFAULT 'BEGINNER',

    FOREIGN KEY (project_id)
        REFERENCES projects(project_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    FOREIGN KEY (skill_id)
        REFERENCES skills(skill_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    UNIQUE(project_id, skill_id),

    CHECK(importance_weight BETWEEN 1 AND 10)
);


-- ============================================================
-- TABLE 7 : TEAMS
-- ============================================================

CREATE TABLE teams (
    team_id INT AUTO_INCREMENT PRIMARY KEY,

    project_id INT NOT NULL,

    team_name VARCHAR(150) NOT NULL,

    team_leader_id INT NOT NULL,

    max_members INT NOT NULL,

    team_status ENUM(
        'FORMING',
        'ACTIVE',
        'COMPLETED',
        'DISBANDED'
    ) DEFAULT 'FORMING',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id)
        REFERENCES projects(project_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    FOREIGN KEY (team_leader_id)
        REFERENCES students(student_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CHECK(max_members > 0)
);


-- ============================================================
-- TABLE 8 : TEAM_MEMBERS
-- ============================================================

CREATE TABLE team_members (
    team_member_id INT AUTO_INCREMENT PRIMARY KEY,

    team_id INT NOT NULL,

    student_id INT NOT NULL,

    member_role ENUM(
        'LEADER',
        'BACKEND_DEVELOPER',
        'FRONTEND_DEVELOPER',
        'DATABASE_DESIGNER',
        'ML_ENGINEER',
        'UI_UX_DESIGNER',
        'OTHER'
    ) DEFAULT 'OTHER',

    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    member_status ENUM(
        'ACTIVE',
        'INACTIVE',
        'REMOVED'
    ) DEFAULT 'ACTIVE',

    FOREIGN KEY (team_id)
        REFERENCES teams(team_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    FOREIGN KEY (student_id)
        REFERENCES students(student_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    UNIQUE(team_id, student_id)
);


-- ============================================================
-- TABLE 9 : JOIN_REQUESTS
-- ============================================================

CREATE TABLE join_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,

    project_id INT NOT NULL,

    sender_student_id INT NOT NULL,

    receiver_student_id INT NOT NULL,

    message TEXT,

    request_status ENUM(
        'PENDING',
        'ACCEPTED',
        'REJECTED',
        'CANCELLED'
    ) DEFAULT 'PENDING',

    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    responded_at TIMESTAMP NULL,

    FOREIGN KEY (project_id)
        REFERENCES projects(project_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    FOREIGN KEY (sender_student_id)
        REFERENCES students(student_id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,

    FOREIGN KEY (receiver_student_id)
        REFERENCES students(student_id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,

    CHECK(sender_student_id <> receiver_student_id)
);


-- ============================================================
-- TABLE 10 : TEAM_CONNECTIONS
-- ============================================================

CREATE TABLE team_connections (
    connection_id INT AUTO_INCREMENT PRIMARY KEY,

    student_id_1 INT NOT NULL,

    student_id_2 INT NOT NULL,

    connection_strength INT DEFAULT 1,

    connection_type ENUM(
        'PREVIOUS_TEAMMATE',
        'CURRENT_TEAMMATE',
        'PROJECT_COLLABORATOR',
        'MUTUAL_CONNECTION'
    ) NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (student_id_1)
        REFERENCES students(student_id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,

    FOREIGN KEY (student_id_2)
        REFERENCES students(student_id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,

    CHECK(student_id_1 <> student_id_2),

    CHECK(connection_strength BETWEEN 1 AND 100)
);


-- ============================================================
-- PART B : INSERT DATA
-- ============================================================


-- ============================================================
-- INSERT DEPARTMENTS
-- ============================================================

INSERT INTO departments
(department_name, department_code)
VALUES
('Computer Engineering', 'COMP'),
('Information Technology', 'IT'),
('Electronics and Telecommunication Engineering', 'ENTC'),
('Artificial Intelligence and Data Science', 'AIDS'),
('Mechanical Engineering', 'MECH');


-- ============================================================
-- INSERT SKILLS
-- ============================================================

INSERT INTO skills
(skill_name, skill_category, description)
VALUES
('Python', 'Programming', 'Python programming'),
('Java', 'Programming', 'Java programming'),
('C', 'Programming', 'C programming'),
('C++', 'Programming', 'C++ programming'),
('SQL', 'Database', 'SQL database programming'),
('MySQL', 'Database', 'MySQL database management'),
('Flask', 'Web Development', 'Python Flask framework'),
('Django', 'Web Development', 'Django framework'),
('React', 'Web Development', 'React frontend framework'),
('HTML', 'Web Development', 'HTML development'),
('CSS', 'Web Development', 'CSS styling'),
('JavaScript', 'Web Development', 'JavaScript programming'),
('Machine Learning', 'Artificial Intelligence', 'Machine learning'),
('Deep Learning', 'Artificial Intelligence', 'Deep learning'),
('Data Science', 'Data', 'Data science'),
('UI/UX Design', 'Design', 'UI and UX design'),
('Figma', 'Design', 'Figma designing'),
('Git', 'Tools', 'Version control'),
('GitHub', 'Tools', 'GitHub'),
('Cybersecurity', 'Security', 'Cybersecurity');


-- ============================================================
-- INSERT STUDENTS
-- ============================================================

INSERT INTO students
(first_name, last_name, email, password_hash,
 department_id, year_of_study, college, bio,
 github_portfolio, experience_level,
 availability_status, account_status)
VALUES

('Ananya','Handoo','ananya@example.com',
 'hash_ananya',
 3,3,'Cummins College',
 'Interested in AI and software development',
 'github.com/ananya',
 'ADVANCED','AVAILABLE','ACTIVE'),

('Riya','Sharma','riya@example.com',
 'hash_riya',
 1,3,'Example College',
 'Full stack developer',
 'github.com/riya',
 'ADVANCED','AVAILABLE','ACTIVE'),

('Sneha','Patil','sneha@example.com',
 'hash_sneha',
 2,2,'Example College',
 'UI UX designer',
 'github.com/sneha',
 'INTERMEDIATE','PARTIALLY_AVAILABLE','ACTIVE'),

('Priya','Deshmukh','priya@example.com',
 'hash_priya',
 4,3,'Example College',
 'Machine learning enthusiast',
 'github.com/priya',
 'ADVANCED','AVAILABLE','ACTIVE'),

('Aarav','Kulkarni','aarav@example.com',
 'hash_aarav',
 1,2,'Example College',
 'Backend developer',
 'github.com/aarav',
 'INTERMEDIATE','AVAILABLE','ACTIVE'),

('Ishita','Joshi','ishita@example.com',
 'hash_ishita',
 3,3,'Example College',
 'Interested in databases',
 'github.com/ishita',
 'ADVANCED','AVAILABLE','ACTIVE'),

('Rahul','Shinde','rahul@example.com',
 'hash_rahul',
 2,4,'Example College',
 'Cybersecurity student',
 'github.com/rahul',
 'EXPERT','NOT_AVAILABLE','ACTIVE'),

('Neha','Desai','neha@example.com',
 'hash_neha',
 4,2,'Example College',
 'Data science student',
 'github.com/neha',
 'INTERMEDIATE','AVAILABLE','ACTIVE'),

('Karan','Pawar','karan@example.com',
 'hash_karan',
 1,4,'Example College',
 'Java developer',
 'github.com/karan',
 'EXPERT','AVAILABLE','ACTIVE'),

('Meera','Shah','meera@example.com',
 'hash_meera',
 3,2,'Example College',
 'Frontend developer',
 'github.com/meera',
 'INTERMEDIATE','AVAILABLE','ACTIVE');


-- ============================================================
-- INSERT STUDENT SKILLS
-- ============================================================

INSERT INTO student_skills
(student_id, skill_id, proficiency_level, years_of_experience)
VALUES

(1,1,'ADVANCED',2),
(1,5,'ADVANCED',2),
(1,7,'INTERMEDIATE',1),
(1,13,'ADVANCED',2),
(1,18,'INTERMEDIATE',1),

(2,2,'ADVANCED',2),
(2,9,'ADVANCED',2),
(2,10,'ADVANCED',2),
(2,11,'ADVANCED',2),
(2,12,'ADVANCED',2),

(3,9,'INTERMEDIATE',1),
(3,11,'INTERMEDIATE',1),
(3,16,'ADVANCED',2),
(3,17,'ADVANCED',2),

(4,1,'ADVANCED',2),
(4,5,'INTERMEDIATE',1),
(4,13,'ADVANCED',2),
(4,14,'INTERMEDIATE',1),
(4,15,'ADVANCED',2),

(5,1,'INTERMEDIATE',1),
(5,7,'ADVANCED',2),
(5,18,'INTERMEDIATE',1),

(6,5,'ADVANCED',3),
(6,6,'ADVANCED',2),
(6,18,'ADVANCED',2),

(7,3,'ADVANCED',2),
(7,20,'EXPERT',3),

(8,1,'INTERMEDIATE',1),
(8,13,'INTERMEDIATE',1),
(8,15,'ADVANCED',2),

(9,2,'EXPERT',4),
(9,4,'ADVANCED',3),

(10,9,'INTERMEDIATE',1),
(10,10,'ADVANCED',2),
(10,11,'ADVANCED',2);


-- ============================================================
-- INSERT PROJECTS
-- ============================================================

INSERT INTO projects
(created_by, project_title, project_description,
 domain, max_team_size, current_team_size,
 difficulty_level, deadline, project_status)
VALUES

(1,
 'AI Movie Recommendation System',
 'Develop an AI based movie recommendation system.',
 'Artificial Intelligence',
 4,1,'HARD','2026-12-31','OPEN'),

(2,
 'College Event Management System',
 'Web application for managing college events.',
 'Web Development',
 5,1,'MEDIUM','2026-11-30','OPEN'),

(4,
 'Student Performance Predictor',
 'Machine learning model to predict student performance.',
 'Data Science',
 4,1,'HARD','2027-01-15','OPEN'),

(6,
 'College Cybersecurity Portal',
 'Security monitoring portal for college systems.',
 'Cybersecurity',
 5,1,'HARD','2027-02-28','OPEN');


-- ============================================================
-- INSERT PROJECT REQUIRED SKILLS
-- ============================================================

INSERT INTO project_required_skills
(project_id, skill_id, importance_weight, minimum_proficiency)
VALUES

(1,1,10,'INTERMEDIATE'),
(1,5,9,'INTERMEDIATE'),
(1,7,8,'INTERMEDIATE'),
(1,13,10,'ADVANCED'),

(2,9,10,'INTERMEDIATE'),
(2,10,8,'BEGINNER'),
(2,11,8,'BEGINNER'),
(2,12,9,'INTERMEDIATE'),

(3,1,10,'INTERMEDIATE'),
(3,5,8,'INTERMEDIATE'),
(3,13,10,'ADVANCED'),
(3,15,9,'INTERMEDIATE'),

(4,3,8,'INTERMEDIATE'),
(4,20,10,'ADVANCED');


-- ============================================================
-- INSERT TEAMS
-- ============================================================

INSERT INTO teams
(project_id, team_name, team_leader_id,
 max_members, team_status)
VALUES

(1,'AI Movie Team',1,4,'FORMING'),
(2,'Event Management Team',2,5,'FORMING'),
(3,'Prediction Team',4,4,'FORMING'),
(4,'Security Team',6,5,'FORMING');


-- ============================================================
-- INSERT TEAM MEMBERS
-- ============================================================

INSERT INTO team_members
(team_id, student_id, member_role, member_status)
VALUES

(1,1,'LEADER','ACTIVE'),
(2,2,'LEADER','ACTIVE'),
(3,4,'LEADER','ACTIVE'),
(4,6,'LEADER','ACTIVE');


-- ============================================================
-- INSERT JOIN REQUESTS
-- ============================================================

INSERT INTO join_requests
(project_id, sender_student_id,
 receiver_student_id, message, request_status)
VALUES

(1,4,1,
 'I am interested in ML and would like to join.',
 'PENDING'),

(1,5,1,
 'I can work on backend development.',
 'PENDING'),

(2,3,2,
 'I can contribute to UI/UX.',
 'PENDING'),

(3,8,4,
 'I am interested in data science.',
 'PENDING'),

(4,7,6,
 'I am interested in cybersecurity.',
 'PENDING');


-- ============================================================
-- INSERT TEAM CONNECTIONS
-- ============================================================

INSERT INTO team_connections
(student_id_1, student_id_2,
 connection_strength, connection_type)
VALUES

(1,4,80,'PROJECT_COLLABORATOR'),
(1,2,60,'PREVIOUS_TEAMMATE'),
(2,3,70,'MUTUAL_CONNECTION'),
(4,8,85,'PROJECT_COLLABORATOR'),
(6,7,90,'CURRENT_TEAMMATE');


-- ============================================================
-- PART C : 70 SQL QUERIES
-- ============================================================


-- ============================================================
-- BASIC SELECT QUERIES
-- ============================================================

-- QUERY 1
SELECT * FROM departments;

-- QUERY 2
SELECT * FROM students;

-- QUERY 3
SELECT * FROM skills;

-- QUERY 4
SELECT * FROM projects;

-- QUERY 5
SELECT * FROM teams;

-- QUERY 6
SELECT * FROM join_requests;

-- QUERY 7
SELECT * FROM team_connections;

-- QUERY 8
SELECT *
FROM students
WHERE account_status = 'ACTIVE';

-- QUERY 9
SELECT *
FROM students
WHERE availability_status = 'AVAILABLE';

-- QUERY 10
SELECT *
FROM students
WHERE experience_level = 'ADVANCED';

-- ============================================================
-- FILTERING AND SORTING
-- ============================================================

-- QUERY 11
SELECT *
FROM students
WHERE year_of_study = 3;

-- QUERY 12
SELECT *
FROM students
WHERE department_id = 3;

-- QUERY 13
SELECT *
FROM students
ORDER BY first_name ASC;

-- QUERY 14
SELECT *
FROM students
ORDER BY experience_level DESC;

-- QUERY 15
SELECT *
FROM projects
WHERE difficulty_level = 'HARD';

-- QUERY 16
SELECT *
FROM projects
WHERE project_status = 'OPEN';

-- QUERY 17
SELECT *
FROM projects
WHERE max_team_size > 4;

-- QUERY 18
SELECT *
FROM projects
WHERE deadline > '2026-12-01';

-- QUERY 19
SELECT *
FROM skills
WHERE skill_category = 'Programming';

-- QUERY 20
SELECT *
FROM skills
WHERE skill_name LIKE 'P%';

-- ============================================================
-- UPDATE QUERIES
-- ============================================================

-- QUERY 21
UPDATE students
SET availability_status = 'PARTIALLY_AVAILABLE'
WHERE student_id = 1;

-- QUERY 22
UPDATE students
SET bio = 'Interested in AI, ML, DBMS and software development.'
WHERE student_id = 1;

-- QUERY 23
UPDATE projects
SET project_status = 'IN_PROGRESS'
WHERE project_id = 1;

-- QUERY 24
UPDATE teams
SET team_status = 'ACTIVE'
WHERE team_id = 1;

-- QUERY 25
UPDATE team_connections
SET connection_strength = 90
WHERE connection_id = 1;

-- ============================================================
-- DELETE QUERIES
-- ============================================================

-- QUERY 26
-- DELETE FROM team_connections
-- WHERE connection_id = 5;

-- QUERY 27
-- DELETE FROM join_requests
-- WHERE request_id = 5;

-- ============================================================
-- AGGREGATE FUNCTIONS
-- ============================================================

-- QUERY 28
SELECT COUNT(*) AS total_students
FROM students;

-- QUERY 29
SELECT COUNT(*) AS total_projects
FROM projects;

-- QUERY 30
SELECT COUNT(*) AS total_skills
FROM skills;

-- QUERY 31
SELECT COUNT(*) AS available_students
FROM students
WHERE availability_status = 'AVAILABLE';

-- QUERY 32
SELECT domain, COUNT(*) AS project_count
FROM projects
GROUP BY domain;

-- QUERY 33
SELECT experience_level, COUNT(*) AS student_count
FROM students
GROUP BY experience_level;

-- QUERY 34
SELECT year_of_study, COUNT(*) AS student_count
FROM students
GROUP BY year_of_study;

-- QUERY 35
SELECT AVG(connection_strength)
AS average_connection_strength
FROM team_connections;

-- QUERY 36
SELECT MAX(connection_strength)
AS highest_connection_strength
FROM team_connections;

-- QUERY 37
SELECT MIN(connection_strength)
AS lowest_connection_strength
FROM team_connections;

-- ============================================================
-- JOINS
-- ============================================================

-- QUERY 38
SELECT
    s.student_id,
    s.first_name,
    s.last_name,
    d.department_name
FROM students s
JOIN departments d
ON s.department_id = d.department_id;

-- QUERY 39
SELECT
    s.first_name,
    s.last_name,
    sk.skill_name,
    ss.proficiency_level
FROM students s
JOIN student_skills ss
ON s.student_id = ss.student_id
JOIN skills sk
ON ss.skill_id = sk.skill_id;

-- QUERY 40
SELECT
    p.project_title,
    s.first_name,
    s.last_name
FROM projects p
JOIN students s
ON p.created_by = s.student_id;

-- QUERY 41
SELECT
    p.project_title,
    sk.skill_name,
    prs.importance_weight
FROM projects p
JOIN project_required_skills prs
ON p.project_id = prs.project_id
JOIN skills sk
ON prs.skill_id = sk.skill_id;

-- QUERY 42
SELECT
    t.team_name,
    p.project_title,
    t.team_status
FROM teams t
JOIN projects p
ON t.project_id = p.project_id;

-- QUERY 43
SELECT
    t.team_name,
    CONCAT(s.first_name,' ',s.last_name)
    AS team_leader
FROM teams t
JOIN students s
ON t.team_leader_id = s.student_id;

-- QUERY 44
SELECT
    t.team_name,
    CONCAT(s.first_name,' ',s.last_name)
    AS student_name,
    tm.member_role
FROM team_members tm
JOIN teams t
ON tm.team_id = t.team_id
JOIN students s
ON tm.student_id = s.student_id;

-- QUERY 45
SELECT
    jr.request_id,
    p.project_title,
    CONCAT(s1.first_name,' ',s1.last_name)
    AS sender,
    CONCAT(s2.first_name,' ',s2.last_name)
    AS receiver,
    jr.request_status
FROM join_requests jr
JOIN projects p
ON jr.project_id = p.project_id
JOIN students s1
ON jr.sender_student_id = s1.student_id
JOIN students s2
ON jr.receiver_student_id = s2.student_id;

-- ============================================================
-- LEFT / RIGHT JOINS
-- ============================================================

-- QUERY 46
SELECT
    s.first_name,
    s.last_name,
    sk.skill_name
FROM students s
LEFT JOIN student_skills ss
ON s.student_id = ss.student_id
LEFT JOIN skills sk
ON ss.skill_id = sk.skill_id;

-- QUERY 47
SELECT
    p.project_title,
    sk.skill_name
FROM projects p
LEFT JOIN project_required_skills prs
ON p.project_id = prs.project_id
LEFT JOIN skills sk
ON prs.skill_id = sk.skill_id;

-- QUERY 48
SELECT
    t.team_name,
    s.first_name,
    s.last_name
FROM teams t
LEFT JOIN team_members tm
ON t.team_id = tm.team_id
LEFT JOIN students s
ON tm.student_id = s.student_id;

-- ============================================================
-- GROUP BY / HAVING
-- ============================================================

-- QUERY 49
SELECT
    d.department_name,
    COUNT(s.student_id) AS total_students
FROM departments d
JOIN students s
ON d.department_id = s.department_id
GROUP BY d.department_id, d.department_name
HAVING COUNT(s.student_id) > 1;

-- QUERY 50
SELECT
    sk.skill_name,
    COUNT(ss.student_id) AS student_count
FROM skills sk
JOIN student_skills ss
ON sk.skill_id = ss.skill_id
GROUP BY sk.skill_id, sk.skill_name
HAVING COUNT(ss.student_id) > 1;

-- QUERY 51
SELECT
    domain,
    COUNT(*) AS project_count
FROM projects
GROUP BY domain
HAVING COUNT(*) > 1;

-- ============================================================
-- SUBQUERIES
-- ============================================================

-- QUERY 52
SELECT
    s.student_id,
    s.first_name,
    s.last_name
FROM students s
JOIN student_skills ss
ON s.student_id = ss.student_id
GROUP BY s.student_id, s.first_name, s.last_name
HAVING COUNT(ss.skill_id) >
(
    SELECT AVG(skill_count)
    FROM
    (
        SELECT COUNT(*) AS skill_count
        FROM student_skills
        GROUP BY student_id
    ) AS temp
);

-- QUERY 53
SELECT *
FROM students
WHERE student_id IN
(
    SELECT student_id
    FROM student_skills
    WHERE skill_id =
    (
        SELECT skill_id
        FROM skills
        WHERE skill_name = 'Python'
    )
);

-- QUERY 54
SELECT *
FROM students
WHERE student_id IN
(
    SELECT student_id
    FROM student_skills
    WHERE skill_id =
    (
        SELECT skill_id
        FROM skills
        WHERE skill_name = 'Machine Learning'
    )
);

-- QUERY 55
SELECT *
FROM projects
WHERE project_id IN
(
    SELECT project_id
    FROM project_required_skills
    WHERE skill_id =
    (
        SELECT skill_id
        FROM skills
        WHERE skill_name = 'Python'
    )
);

-- QUERY 56
SELECT *
FROM students
WHERE student_id IN
(
    SELECT student_id
    FROM student_skills
    WHERE proficiency_level = 'ADVANCED'
);

-- ============================================================
-- EXISTS / NOT EXISTS
-- ============================================================

-- QUERY 57
SELECT *
FROM students s
WHERE EXISTS
(
    SELECT 1
    FROM student_skills ss
    WHERE ss.student_id = s.student_id
);

-- QUERY 58
SELECT *
FROM students s
WHERE NOT EXISTS
(
    SELECT 1
    FROM join_requests jr
    WHERE jr.sender_student_id = s.student_id
);

-- QUERY 59
SELECT *
FROM projects p
WHERE EXISTS
(
    SELECT 1
    FROM project_required_skills prs
    WHERE prs.project_id = p.project_id
);

-- ============================================================
-- CASE STATEMENTS
-- ============================================================

-- QUERY 60
SELECT
    first_name,
    last_name,
    experience_level,

    CASE
        WHEN experience_level = 'EXPERT'
            THEN 'Highly Experienced'

        WHEN experience_level = 'ADVANCED'
            THEN 'Experienced'

        WHEN experience_level = 'INTERMEDIATE'
            THEN 'Moderately Experienced'

        ELSE 'Beginner'
    END AS experience_category

FROM students;

-- QUERY 61
SELECT
    project_title,
    difficulty_level,

    CASE
        WHEN difficulty_level = 'HARD'
            THEN 'High Difficulty'

        WHEN difficulty_level = 'MEDIUM'
            THEN 'Moderate Difficulty'

        ELSE 'Low Difficulty'
    END AS difficulty_category

FROM projects;

-- ============================================================
-- STRING FUNCTIONS
-- ============================================================

-- QUERY 62
SELECT
    CONCAT(first_name,' ',last_name)
    AS full_name
FROM students;

-- QUERY 63
SELECT
    UPPER(project_title)
    AS project_name
FROM projects;

-- QUERY 64
SELECT
    first_name,
    LENGTH(first_name) AS name_length
FROM students;

-- ============================================================
-- DATE FUNCTIONS
-- ============================================================

-- QUERY 65
SELECT
    project_title,
    deadline,
    DATEDIFF(deadline,CURDATE())
    AS days_remaining
FROM projects;

-- QUERY 66
SELECT *
FROM projects
WHERE YEAR(created_at) = YEAR(CURDATE());

-- ============================================================
-- VIEWS
-- ============================================================

-- QUERY 67
CREATE OR REPLACE VIEW student_skill_view AS
SELECT
    s.student_id,
    CONCAT(s.first_name,' ',s.last_name)
    AS student_name,
    sk.skill_name,
    ss.proficiency_level,
    ss.years_of_experience
FROM students s
JOIN student_skills ss
ON s.student_id = ss.student_id
JOIN skills sk
ON ss.skill_id = sk.skill_id;

-- QUERY 68
CREATE OR REPLACE VIEW project_details_view AS
SELECT
    p.project_id,
    p.project_title,
    p.domain,
    p.difficulty_level,
    p.deadline,
    p.project_status,
    CONCAT(s.first_name,' ',s.last_name)
    AS project_creator
FROM projects p
JOIN students s
ON p.created_by = s.student_id;

-- QUERY 69
SELECT *
FROM student_skill_view;

-- QUERY 70
SELECT *
FROM project_details_view;

-- ============================================================
-- END OF DATABASE
-- ============================================================