
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID，主键自增',
    name VARCHAR(50) NOT NULL COMMENT '用户名，必填',
    email VARCHAR(100) UNIQUE NOT NULL COMMENT '邮箱，唯一且必填',
    age TINYINT NULL COMMENT '年龄，可选',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间，自动记录'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户测试表';
INSERT INTO users (name, email, age) VALUES
('张三', 'zhangsan@example.com', 25),
('李四', 'lisi@example.com', 30),
('王五', 'wangwu@example.com', 28);
select * from users;


CREATE TABLE IF NOT EXISTS student_scores (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '序号，主键自增',
    name VARCHAR(50) NOT NULL COMMENT '姓名',
    chinese TINYINT NOT NULL COMMENT '语文',
    math TINYINT NOT NULL COMMENT '数学',
    english TINYINT NOT NULL COMMENT '英语',
    physics TINYINT NOT NULL COMMENT '物理',
    chemistry TINYINT NOT NULL COMMENT '化学',
    biology TINYINT NOT NULL COMMENT '生物',
    history TINYINT NOT NULL COMMENT '历史',
    geography TINYINT NOT NULL COMMENT '地理',
    politics TINYINT NOT NULL COMMENT '政治',
    total_score INT NOT NULL COMMENT '总分'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生成绩表';


INSERT INTO student_scores (name, chinese, math, english, physics, chemistry, biology, history, geography, politics, total_score) VALUES
('王小明', 85, 92, 88, 78, 82, 75, 80, 77, 83, 790),
('李华', 78, 89, 90, 85, 88, 82, 76, 84, 86, 818),
('张敏', 90, 83, 86, 91, 87, 88, 82, 85, 89, 841),
('陈刚', 82, 95, 80, 88, 90, 86, 83, 80, 81, 825),
('刘芳', 76, 82, 84, 79, 83, 78, 75, 77, 80, 774),
('杨威', 88, 90, 82, 92, 89, 87, 84, 86, 85, 843),
('吴静', 91, 86, 89, 84, 85, 83, 81, 88, 87, 824),
('赵鹏', 80, 93, 81, 87, 92, 84, 80, 83, 82, 812),
('孙悦', 79, 85, 87, 76, 80, 77, 78, 79, 81, 772),
('周琳', 84, 88, 91, 82, 86, 85, 83, 84, 88, 825),
('郑浩', 86, 91, 83, 89, 88, 86, 82, 85, 84, 836),
('冯雪', 77, 84, 88, 75, 81, 74, 76, 78, 80, 773),
('田甜', 92, 87, 85, 90, 89, 88, 84, 86, 87, 848),
('贺磊', 81, 94, 82, 86, 91, 85, 81, 82, 83, 815),
('钟莹', 78, 83, 86, 79, 84, 77, 75, 78, 81, 771),
('姜涛', 87, 90, 84, 91, 88, 86, 83, 85, 84, 838),
('段丽', 90, 86, 89, 85, 87, 84, 82, 86, 88, 837),
('侯宇', 83, 92, 81, 88, 90, 87, 80, 83, 82, 816),
('袁梦', 76, 85, 88, 77, 82, 76, 78, 79, 80, 771),
('文轩', 88, 91, 85, 90, 89, 88, 84, 86, 87, 848);

-- 创建家庭联系表
CREATE TABLE `family_contact` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '序号',
    `father_name` VARCHAR(20) NOT NULL COMMENT '父亲姓名',
    `mother_name` VARCHAR(20) NOT NULL COMMENT '母亲姓名',
    `father_phone` VARCHAR(11) NOT NULL COMMENT '父亲电话',
    `mother_phone` VARCHAR(11) NOT NULL COMMENT '母亲电话',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='家庭联系表';

-- 插入家庭联系表数据
INSERT INTO `family_contact` (`id`, `father_name`, `mother_name`, `father_phone`, `mother_phone`) VALUES
(1,  '王强',   '李梅', '13800138000', '13900139000'),
(2,  '李军',   '张华', '13600136000', '13700137000'),
(3,  '张勇',   '陈丽', '13500135000', '13400134000'),
(4,  '陈一刚', '周敏', '13200132000', '13300133000'),
(5,  '刘辉',   '杨娟', '13100131000', '13000130000'),
(6,  '杨明',   '赵芳', '14700147000', '14800148000'),
(7,  '吴俊',   '孙燕', '14900149000', '15000150000'),
(8,  '赵刚',   '钱丽', '15100151000', '15200152000'),
(9,  '孙林',   '何娜', '15300153000', '15400154000'),
(10, '周建',   '徐慧', '15500155000', '15600156000'),
(11, '郑华',   '马丽', '15700157000', '15800158000'),
(12, '冯峰',   '朱婷', '15900159000', '16000160000'),
(13, '田军',   '高敏', '16100161000', '16200162000'),
(14, '贺伟',   '郭玲', '16300163000', '16400164000'),
(15, '钟明',   '罗霞', '16500165000', '16600166000'),
(16, '姜云涛', '唐瑶', '16700167000', '16800168000'),
(17, '段勇',   '谢红', '16900169000', '17000170000'),
(18, '侯军',   '卢芳', '17100171000', '17200172000'),
(19, '袁刚',   '黄琴', '17300173000', '17400174000');

-- 创建身体状况表
CREATE TABLE `physical_condition` (
    `id`       INT NOT NULL AUTO_INCREMENT COMMENT '序号',
    `height`   DECIMAL(5,1) NOT NULL COMMENT '身高',
    `weight`   DECIMAL(5,1) NOT NULL COMMENT '体重',
    `age`      INT NOT NULL COMMENT '年龄（岁）',
    `gender`   ENUM('男','女') NOT NULL COMMENT '性别',
    `body_fat` DECIMAL(4,1) NOT NULL COMMENT '体脂（%）',
    `blood_sugar` DECIMAL(3,1) NOT NULL COMMENT '血糖',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='身体状况表';

-- 插入身体状况表数据
INSERT INTO `physical_condition` (`id`, `height`, `weight`, `age`, `gender`, `body_fat`, `blood_sugar`) VALUES
(1,  175, 70, 20, '男', 18, 5.5),
(2,  168, 55, 19, '女', 22, 5.2),
(3,  180, 75, 21, '男', 16, 5.8),
(4,  172, 68, 20, '男', 17, 5.3),
(5,  165, 52, 18, '女', 20, 5.0),
(6,  178, 73, 22, '男', 19, 5.6),
(7,  160, 50, 19, '女', 21, 5.1),
(8,  173, 66, 20, '男', 18, 5.4),
(9,  170, 64, 21, '男', 19, 5.7),
(10, 162, 53, 18, '女', 20, 5.2),
(11, 176, 71, 22, '男', 18, 5.5),
(12, 166, 56, 19, '女', 21, 5.3),
(13, 182, 78, 23, '男', 17, 5.9),
(14, 174, 69, 20, '男', 18, 5.4),
(15, 164, 51, 18, '女', 20, 5.0),
(16, 177, 72, 21, '男', 19, 5.6),
(17, 163, 54, 19, '女', 21, 5.2),
(18, 171, 67, 20, '男', 18, 5.3),
(19, 167, 58, 18, '女', 20, 5.1),
(20, 179, 74, 22, '男', 17, 5.7);


