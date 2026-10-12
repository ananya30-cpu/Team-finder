-- ============================================================
-- COLLEGE PROJECT TEAM FINDER
-- SELECTED 30 SQL QUERIES (from Part C)
-- ============================================================


-- ============================================================
-- BASIC SELECT QUERIES
-- ============================================================

-- QUERY 1
SELECT *
FROM students
WHERE availability_status = 'AVAILABLE';


-- ============================================================
-- FILTERING AND SORTING
-- ============================================================

-- QUERY 2
SELECT *
FROM students
ORDER BY experience_level DESC;

-- QUERY 3
SELECT *
FROM projects
WHERE deadline > '2026-12-01';


-- ============================================================
-- UPDATE QUERIES
-- ============================================================

-- QUERY 4
UPDATE students
SET availability_status = 'PARTIALLY_AVAILABLE'
WHERE student_id = 1;

-- QUERY 5
UPDATE team_connections
SET connection_strength = 90
WHERE connection_id = 1;


-- ============================================================
-- DELETE QUERIES
-- ============================================================

-- QUERY 6
-- DELETE FROM team_connections
-- WHERE connection_id = 5;


-- ============================================================
-- AGGREGATE FUNCTIONS
-- ============================================================

-- QUERY 7
SELECT COUNT(*) AS total_students
FROM students;

-- QUERY 8
SELECT domain, COUNT(*) AS project_count
FROM projects
GROUP BY domain;

-- QUERY 9
SELECT experience_level, COUNT(*) AS student_count
FROM students
GROUP BY experience_level;

-- QUERY 10
SELECT AVG(connection_strength)
AS average_connection_strength
FROM team_connections;


-- ============================================================
-- JOINS
-- ============================================================

-- QUERY 11
SELECT
    s.student_id,
    s.first_name,
    s.last_name,
    d.department_name
FROM students s
JOIN departments d
ON s.department_id = d.department_id;

-- QUERY 12
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

-- QUERY 13
SELECT
    p.project_title,
    sk.skill_name,
    prs.importance_weight
FROM projects p
JOIN project_required_skills prs
ON p.project_id = prs.project_id
JOIN skills sk
ON prs.skill_id = sk.skill_id;

-- QUERY 14
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

-- QUERY 15
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

-- QUERY 16
SELECT
    s.first_name,
    s.last_name,
    sk.skill_name
FROM students s
LEFT JOIN student_skills ss
ON s.student_id = ss.student_id
LEFT JOIN skills sk
ON ss.skill_id = sk.skill_id;


-- ============================================================
-- GROUP BY / HAVING
-- ============================================================

-- QUERY 17
SELECT
    d.department_name,
    COUNT(s.student_id) AS total_students
FROM departments d
JOIN students s
ON d.department_id = s.department_id
GROUP BY d.department_id, d.department_name
HAVING COUNT(s.student_id) > 1;

-- QUERY 18
SELECT
    sk.skill_name,
    COUNT(ss.student_id) AS student_count
FROM skills sk
JOIN student_skills ss
ON sk.skill_id = ss.skill_id
GROUP BY sk.skill_id, sk.skill_name
HAVING COUNT(ss.student_id) > 1;


-- ============================================================
-- SUBQUERIES
-- ============================================================

-- QUERY 19
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

-- QUERY 20
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

-- QUERY 21
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


-- ============================================================
-- EXISTS / NOT EXISTS
-- ============================================================

-- QUERY 22
SELECT *
FROM students s
WHERE EXISTS
(
    SELECT 1
    FROM student_skills ss
    WHERE ss.student_id = s.student_id
);

-- QUERY 23
SELECT *
FROM students s
WHERE NOT EXISTS
(
    SELECT 1
    FROM join_requests jr
    WHERE jr.sender_student_id = s.student_id
);


-- ============================================================
-- CASE STATEMENTS
-- ============================================================

-- QUERY 24
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


-- ============================================================
-- STRING FUNCTIONS
-- ============================================================

-- QUERY 25
SELECT
    CONCAT(first_name,' ',last_name)
    AS full_name
FROM students;


-- ============================================================
-- DATE FUNCTIONS
-- ============================================================

-- QUERY 26
SELECT
    project_title,
    deadline,
    DATEDIFF(deadline,CURDATE())
    AS days_remaining
FROM projects;


-- ============================================================
-- VIEWS
-- ============================================================

-- QUERY 27
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

-- QUERY 28
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

-- QUERY 29
SELECT *
FROM student_skill_view;

-- QUERY 30
SELECT *
FROM project_details_view;
