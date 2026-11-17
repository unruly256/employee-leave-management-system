# Project folder guide

```text
leave_project/
├── general_settings/                 # Django project settings and root URLs
├── leave/                            # Employee leave Django application
│   ├── migrations/                   # Database migration history
│   ├── management/commands/          # seed_leave: optional demo-data command
│   ├── templatetags/leave_tags.py    # Filters and tags: status badge, date ranges, paging links
│   ├── templates/
│   │   ├── leave/                    # Pages for the app (all extend base.html)
│   │   ├── registration/             # Sign-in page
│   │   └── 403.html 404.html 500.html  # Branded error pages
│   ├── static/leave/
│   │   ├── css/style.css             # Application styles (design tokens at the top)
│   │   ├── js/app.js                 # Confirmation dialog, double-submit guard, flash messages
│   │   ├── js/leave-form.js          # Live day-count preview on the apply form
│   │   └── vendor/                   # Bootstrap, Bootstrap Icons, IBM Plex Sans (local copies)
│   ├── context_processors.py         # Puts the signed-in user's role in every page
│   ├── models.py                     # Database models and business rules
│   ├── forms.py                      # Forms (Bootstrap-styled through StyledFormMixin)
│   ├── views.py                      # Request handling
│   ├── urls.py                       # App URL routes
│   ├── permissions.py                # Role and access checks
│   ├── utils.py                      # Working-day and public-holiday counting
│   ├── admin.py                      # Django admin registration
│   └── tests.py                      # Automated tests
├── docs/                             # Project documentation
├── manage.py                         # Django command entry point
├── requirements.txt                  # Python dependencies
├── .env.example                      # Template for local settings
├── setup_project.bat                 # First-time Windows setup
└── run_project.bat                   # Windows run helper
```

Every page template extends `leave/templates/leave/base.html`, which loads the local Bootstrap,
the stylesheet and the scripts. Page-specific additions go in that template's `extra_css` or
`extra_js` block. Change colours and spacing in the `:root` block at the top of `style.css`.
