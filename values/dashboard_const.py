dashboards = {
    "admin": [
        {
            'title': 'Account Registration',
            'description': 'Register a new account for professor/lab technician/student to access this system',
            'link': [
                {
                    'content': 'Register Account',
                    'href': "/register_account"
                }
            ]
        },
        {
            'title': 'Class Management',
            'description': 'Upload professor and student timetable from NTU into this system',
            'link': [
                {
                    'content': 'Professor Timetable',
                    'href': '/upload_professor_timetable'
                },
                {
                    'content': 'Student Timetable',
                    'href': '/upload_professor_timetable'
                }
            ]
        }
    ],
    "staff": [
        {
            'title': 'View Classes',
            'description': "Check the attendance of the classes that you are teaching",
            'link': [
                {
                    'content': 'View Classes',
                    'href': '/view_classes'
                }
            ]
        }
    ],
    "student": [
        {
            "title": 'Facial Image',
            'description': 'Upload new facial images into the system',
            'link': [
                {
                    'content': 'Upload Image',
                    'href': '/upload_image'
                }
            ]
        }
    ]
}
