from sqlalchemy.orm import Session
from app.models.pricing_rule import PricingRule
from app.schemas.pricing_rule import PricingRuleCreate, PricingRuleUpdate

def create_pricing_rule(db: Session, rule: PricingRuleCreate):
    db_rule = PricingRule(**rule.dict())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

def get_pricing_rules(db: Session, skip: int = 0, limit: int = 100):
    return db.query(PricingRule).offset(skip).limit(limit).all()

def get_pricing_rule(db: Session, rule_id: str):
    return db.query(PricingRule).filter(PricingRule.rule_id == rule_id).first()

def update_pricing_rule(db: Session, rule_id: str, rule_update: PricingRuleUpdate):
    db_rule = db.query(PricingRule).filter(PricingRule.rule_id == rule_id).first()
    if not db_rule:
        return None

    for key, value in rule_update.dict(exclude_unset=True).items():
        setattr(db_rule, key, value)

    db.commit()
    db.refresh(db_rule)
    return db_rule

def deactivate_pricing_rule(db: Session, rule_id: str):
    db_rule = db.query(PricingRule).filter(PricingRule.rule_id == rule_id).first()
    if not db_rule:
        return None
    db_rule.status = "inactive"
    db.commit()
    db.refresh(db_rule)
    return db_rule

def activate_pricing_rule(db: Session, rule_id: str):
    db_rule = db.query(PricingRule).filter(PricingRule.rule_id == rule_id).first()
    if not db_rule:
        return None
    db_rule.status = "active"
    db.commit()
    db.refresh(db_rule)
    return db_rule
