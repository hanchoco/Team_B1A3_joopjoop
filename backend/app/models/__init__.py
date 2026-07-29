"""Public ORM model registry.

Importing this package registers every mapped table on ``Base.metadata``.
"""

from app.models.notification_setting import (
    Notification,
    NotificationSendStatus,
    NotificationSetting,
    NotificationType,
)
from app.models.policy import (
    AmountType,
    BenefitType,
    PaymentCycle,
    Policy,
    PolicyBenefit,
    PolicyCategory,
    PolicySource,
    PolicyStatus,
)
from app.models.policy_condition import (
    CheckMode,
    ConditionOperator,
    PolicyCondition,
)
from app.models.policy_document import PolicyDocument
from app.models.user import (
    AccountStatus,
    ConsentType,
    EmploymentStatusCode,
    HouseholdTypeCode,
    HousingTypeCode,
    IncomeBandCode,
    User,
    UserConsent,
    UserProfile,
)
from app.models.user_category_profile import (
    AnswerType,
    Category,
    CategoryCode,
    CategoryQuestion,
    UserCategoryAnswer,
)
from app.models.user_document_progress import (
    DocumentPreparationStatus,
    UserDocumentCheck,
    UserDocumentProgress,
)
from app.models.user_policy import (
    ApplicationStatus,
    ConditionResultStatus,
    EligibilityStatus,
    PreparationStatus,
    UserPolicyConditionResult,
    UserPolicyMatch,
    UserPolicyState,
)

__all__ = [
    "AccountStatus",
    "AmountType",
    "AnswerType",
    "ApplicationStatus",
    "BenefitType",
    "Category",
    "CategoryCode",
    "CategoryQuestion",
    "CheckMode",
    "ConditionOperator",
    "ConditionResultStatus",
    "ConsentType",
    "DocumentPreparationStatus",
    "EligibilityStatus",
    "EmploymentStatusCode",
    "HouseholdTypeCode",
    "HousingTypeCode",
    "IncomeBandCode",
    "Notification",
    "NotificationSendStatus",
    "NotificationSetting",
    "NotificationType",
    "PaymentCycle",
    "Policy",
    "PolicyBenefit",
    "PolicyCategory",
    "PolicyCondition",
    "PolicyDocument",
    "PolicySource",
    "PolicyStatus",
    "PreparationStatus",
    "User",
    "UserCategoryAnswer",
    "UserConsent",
    "UserDocumentCheck",
    "UserDocumentProgress",
    "UserPolicyConditionResult",
    "UserPolicyMatch",
    "UserPolicyState",
    "UserProfile",
]
