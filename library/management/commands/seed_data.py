"""
Management command: seed_data
Creates sample categories and publications for development.

Usage:
    python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from library.models import Category, Publication

User = get_user_model()

CATEGORIES = [
    {"name": "Computer Science", "icon": "bi-cpu-fill", "color": "#1B3A6B"},
    {"name": "Life Sciences", "icon": "bi-heart-pulse-fill", "color": "#2E7D32"},
    {"name": "Physics & Mathematics", "icon": "bi-infinity", "color": "#6A1B9A"},
    {"name": "Social Sciences", "icon": "bi-people-fill", "color": "#C9A84C"},
    {"name": "Engineering", "icon": "bi-gear-fill", "color": "#1565C0"},
    {"name": "Medicine & Health", "icon": "bi-hospital-fill", "color": "#C62828"},
    {"name": "Economics", "icon": "bi-graph-up-arrow", "color": "#00695C"},
    {"name": "Environmental Science", "icon": "bi-tree-fill", "color": "#33691E"},
]

PUBLICATIONS = [
    {
        "title": "Deep Learning Fundamentals for Natural Language Processing",
        "author": "Smith, James R.",
        "abstract": "A comprehensive guide to applying deep learning techniques in NLP tasks including transformers, BERT, and GPT architectures.",
        "publication_year": 2023,
        "publication_type": "book",
        "category_name": "Computer Science",
        "publisher": "MIT Press",
        "is_open_access": True,
    },
    {
        "title": "CRISPR-Cas9 Applications in Genetic Therapy: Current State and Future Prospects",
        "author": "Osei, Kwame A.",
        "abstract": "This paper explores the revolutionary applications of CRISPR-Cas9 gene editing technology in treating hereditary diseases.",
        "publication_year": 2023,
        "publication_type": "journal",
        "category_name": "Life Sciences",
        "journal_name": "Nature Biotechnology",
        "volume": "41",
        "issue": "3",
        "is_open_access": True,
    },
    {
        "title": "Quantum Computing Architecture and Fault-Tolerant Algorithms",
        "author": "Zhang, Wei",
        "abstract": "An investigation into quantum gate architectures, qubit coherence, and error correction mechanisms for practical quantum computing.",
        "publication_year": 2022,
        "publication_type": "thesis",
        "category_name": "Physics & Mathematics",
        "institution": "MIT",
        "is_open_access": True,
    },
    {
        "title": "Social Media and Political Polarization: Evidence from 14 Countries",
        "author": "Mensah, Abena",
        "abstract": "A cross-national study examining the relationship between social media usage patterns and political opinion polarization.",
        "publication_year": 2023,
        "publication_type": "journal",
        "category_name": "Social Sciences",
        "journal_name": "American Political Science Review",
        "is_open_access": False,
    },
    {
        "title": "Autonomous Vehicle Safety Systems Using Multi-Sensor Fusion",
        "author": "Patel, Rohan K.",
        "co_authors": "Chen, Lily M., Rodriguez, Carlos",
        "abstract": "This research presents a novel approach to autonomous vehicle safety through the integration of LiDAR, radar, and camera systems.",
        "publication_year": 2023,
        "publication_type": "conference",
        "category_name": "Engineering",
        "publisher": "IEEE",
        "is_open_access": True,
    },
    {
        "title": "Gut Microbiome Diversity and Mental Health: A Meta-Analysis",
        "author": "Appiah, Linda O.",
        "abstract": "A systematic review and meta-analysis of 180 studies examining the bidirectional communication between gut microbiota and brain function.",
        "publication_year": 2023,
        "publication_type": "journal",
        "category_name": "Medicine & Health",
        "journal_name": "Lancet Psychiatry",
        "is_open_access": True,
    },
    {
        "title": "Universal Basic Income: Macroeconomic Effects in Developing Economies",
        "author": "Asante, Emmanuel B.",
        "abstract": "This dissertation evaluates the macroeconomic effects of Universal Basic Income pilots in Ghana, Kenya, and India.",
        "publication_year": 2022,
        "publication_type": "dissertation",
        "category_name": "Economics",
        "institution": "London School of Economics",
        "is_open_access": True,
    },
    {
        "title": "Carbon Sequestration Potential of Mangrove Restoration in West Africa",
        "author": "Boateng, Sandra K.",
        "abstract": "Quantifying carbon sequestration rates in restored mangrove ecosystems along the West African coastline.",
        "publication_year": 2023,
        "publication_type": "journal",
        "category_name": "Environmental Science",
        "journal_name": "Global Change Biology",
        "is_open_access": True,
    },
    {
        "title": "Federated Learning for Privacy-Preserving Healthcare AI",
        "author": "Nguyen, Thi Lan",
        "co_authors": "Owusu, Felix J.",
        "abstract": "A framework for training machine learning models on distributed medical data without compromising patient privacy.",
        "publication_year": 2024,
        "publication_type": "book",
        "category_name": "Computer Science",
        "publisher": "O'Reilly Media",
        "is_open_access": True,
    },
    {
        "title": "Topological Phases and Quantum Field Theory",
        "author": "Kapoor, Ananya",
        "abstract": "A rigorous mathematical treatment of topological phases of matter and their relationship to quantum field theories.",
        "publication_year": 2022,
        "publication_type": "thesis",
        "category_name": "Physics & Mathematics",
        "institution": "Oxford University",
        "is_open_access": False,
    },
    {
        "title": "African Urban Planning: Smart City Infrastructure for Lagos and Accra",
        "author": "Aidoo, Kofi",
        "abstract": "Examining smart city integration challenges and opportunities in rapidly urbanizing African megacities.",
        "publication_year": 2023,
        "publication_type": "report",
        "category_name": "Engineering",
        "institution": "African Development Bank",
        "is_open_access": True,
    },
    {
        "title": "Machine Learning Approaches to Early Cancer Detection",
        "author": "Darko, Priscilla E.",
        "co_authors": "Lee, Jonathan H.",
        "abstract": "Applying convolutional neural networks and transformer architectures to medical imaging for early-stage cancer identification.",
        "publication_year": 2024,
        "publication_type": "journal",
        "category_name": "Medicine & Health",
        "journal_name": "Nature Medicine",
        "is_open_access": True,
    },
]


class Command(BaseCommand):
    help = 'Seed database with sample categories and publications'

    def handle(self, *args, **options):
        self.stdout.write('🌱 Seeding database...\n')

        # Create superuser
        if not User.objects.filter(email='admin@scholarvault.com').exists():
            User.objects.create_superuser(
                email='admin@scholarvault.com',
                username='admin',
                password='admin123',
                first_name='Admin',
                last_name='User',
                is_staff=True,
                is_superuser=True,
            )
            self.stdout.write(self.style.SUCCESS('✅ Superuser created: admin@scholarvault.com / admin123'))

        # Create sample PhD user
        if not User.objects.filter(email='phd@scholarvault.com').exists():
            User.objects.create_user(
                email='phd@scholarvault.com',
                username='phdstudent',
                password='phd123',
                first_name='Sarah',
                last_name='Asante',
                role='phd',
                institution='University of Ghana',
                research_area='Machine Learning',
            )
            self.stdout.write(self.style.SUCCESS('✅ PhD user created: phd@scholarvault.com / phd123'))

        # Create categories
        cat_map = {}
        for cat_data in CATEGORIES:
            cat, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'icon': cat_data['icon'], 'color': cat_data['color']},
            )
            cat_map[cat.name] = cat
            if created:
                self.stdout.write(f'  📚 Category: {cat.name}')

        # Create publications
        count = 0
        for pub_data in PUBLICATIONS:
            category = cat_map.get(pub_data.pop('category_name'))
            tags = pub_data.pop('tags', [])
            if not Publication.objects.filter(title=pub_data['title']).exists():
                pub = Publication.objects.create(category=category, **pub_data)
                if tags:
                    pub.tags.set(*tags)
                count += 1

        self.stdout.write(self.style.SUCCESS(f'\n✅ Done! Created {count} publications across {len(CATEGORIES)} categories.\n'))
        self.stdout.write('  🔑 Admin: admin@scholarvault.com / admin123')
        self.stdout.write('  🎓 PhD User: phd@scholarvault.com / phd123\n')
