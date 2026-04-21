import re

with open('models.py', 'r') as f:
    content = f.read()

choices_classes = """class ResumeType(models.TextChoices):
    ONGOING = 'ONGOING', 'Ongoing'
    COMPLETED = 'COMPLETED', 'Completed'

class AchievementType(models.TextChoices):
    EDUCATIONAL = 'EDUCATIONAL', 'Educational'
    OTHER = 'OTHER', 'Other'

class EventType(models.TextChoices):
    SOCIAL = 'SOCIAL', 'Social'
    CULTURE = 'CULTURE', 'Culture'
    SPORT = 'SPORT', 'Sport'
    OTHER = 'OTHER', 'Other'

class InvitationType(models.TextChoices):
    ACCEPTED = 'ACCEPTED', 'Accepted'
    REJECTED = 'REJECTED', 'Rejected'
    PENDING = 'PENDING', 'Pending'
    IGNORE = 'IGNORE', 'IGNORE'

class PlacementType(models.TextChoices):
    PLACEMENT = 'PLACEMENT', 'Placement'
    PBI = 'PBI', 'PBI'
    HIGHER_STUDIES = 'HIGHER STUDIES', 'Higher Studies'
    OTHER = 'OTHER', 'Other'

class PlacedType(models.TextChoices):
    NOT_PLACED = 'NOT PLACED', 'Not Placed'
    PLACED = 'PLACED', 'Placed'

class DebarType(models.TextChoices):
    NOT_DEBAR = 'NOT DEBAR', 'Not Debar'
    DEBAR = 'DEBAR', 'Debar'

class BtechDep(models.TextChoices):
    CSE = 'CSE', 'CSE'
    ME = 'ME', 'ME'
    ECE = 'ECE', 'ECE'
    SM = 'SM', 'SM'

class BdesDep(models.TextChoices):
    DESIGN = 'DESIGN', 'DESIGN'

class MtechDep(models.TextChoices):
    CSE = 'CSE', 'CSE'
    CAD_CAM = 'CAD/CAM', 'CAD/CAM'
    DESIGN = 'DESIGN', 'DESIGN'
    MANUFACTURING = 'MANUFACTURING', 'MANUFACTURING'
    MECHATRONICS = 'MECHATRONICS', 'MECHATRONICS'

class MdesDep(models.TextChoices):
    DESIGN = 'DESIGN', 'DESIGN'

class PhdDep(models.TextChoices):
    CSE = 'CSE', 'CSE'
    ME = 'ME', 'ME'
    ECE = 'ECE', 'ECE'
    DESIGN = 'DESIGN', 'DESIGN'
    NS = 'NS', 'NS'
"""

# Replace Constants class block
constants_pattern = re.compile(r'class Constants:.*?    \)\n\n', re.DOTALL)
content = constants_pattern.sub(choices_classes + '\n', content)

# Update the usages
replacements = {
    'Constants.RESUME_TYPE': 'ResumeType.choices',
    'Constants.ACHIEVEMENT_TYPE': 'AchievementType.choices',
    'Constants.EVENT_TYPE': 'EventType.choices',
    'Constants.INVITATION_TYPE': 'InvitationType.choices',
    'Constants.PLACEMENT_TYPE': 'PlacementType.choices',
    'Constants.PLACED_TYPE': 'PlacedType.choices',
    'Constants.DEBAR_TYPE': 'DebarType.choices',
    "default='COMPLETED'": "default=ResumeType.COMPLETED",
    "default='OTHER'": "default='OTHER'", # keep string literal for now or change carefully. Wait, AchievementType.OTHER and EventType.OTHER are both 'OTHER'.
    "default='PENDING'": "default=InvitationType.PENDING",
    "default='PLACEMENT'": "default=PlacementType.PLACEMENT",
    "default='NOT PLACED'": "default=PlacedType.NOT_PLACED",
    "default='NOT DEBAR'": "default=DebarType.NOT_DEBAR",
}

for old, new in replacements.items():
    content = content.replace(old, new)

# specific fix for OTHER
content = content.replace(
    "choices=AchievementType.choices,\n                                        default='OTHER'",
    "choices=AchievementType.choices,\n                                        default=AchievementType.OTHER"
)
content = content.replace(
    "choices=EventType.choices,\n                                        default='OTHER'",
    "choices=EventType.choices,\n                                        default=EventType.OTHER"
)
content = content.replace(
    "choices=PlacementType.choices,\n                                      default='PLACEMENT'",
    "choices=PlacementType.choices,\n                                      default=PlacementType.PLACEMENT"
)
content = content.replace(
    "choices=PlacementType.choices,\n                                      default=PlacementType.PLACEMENT",
    "choices=PlacementType.choices,\n                                      default=PlacementType.PLACEMENT"
)

with open('models.py', 'w') as f:
    f.write(content)
