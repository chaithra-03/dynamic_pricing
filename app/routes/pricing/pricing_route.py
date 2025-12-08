from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.pricing_rule import PricingRuleCreate, PricingRuleUpdate, PricingRuleResponse
from app.services.pricing_service.pricing_service import (
    create_pricing_rule, get_pricing_rules, get_pricing_rule,
    update_pricing_rule, deactivate_pricing_rule, activate_pricing_rule
)
from app.dependencies.auth import require_auth, require_admin


router = APIRouter(prefix="/pricing-rules", tags=["Pricing Rules"])

@router.post("/", response_model=PricingRuleResponse, dependencies=[Depends(require_admin)])
def create_rule(rule: PricingRuleCreate, db: Session = Depends(get_db)):
    return create_pricing_rule(db, rule)

@router.get("/", response_model=list[PricingRuleResponse], dependencies=[Depends(require_auth)])
def list_rules(db: Session = Depends(get_db)):
    return get_pricing_rules(db)

@router.put("/{rule_id}", response_model=PricingRuleResponse, dependencies=[Depends(require_admin)])
def update_rule(rule_id: str, rule: PricingRuleUpdate, db: Session = Depends(get_db)):
    updated = update_pricing_rule(db, rule_id, rule)
    if not updated:
        raise HTTPException(status_code=404, detail="Rule not found")
    return updated

@router.delete("/{rule_id}", response_model=PricingRuleResponse,dependencies=[Depends(require_admin)])
def deactivate_rule(rule_id: str, db: Session = Depends(get_db)):
    rule = deactivate_pricing_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule

@router.post("/{rule_id}/activate", response_model=PricingRuleResponse, dependencies=[Depends(require_admin)])
def activate_rule(rule_id: str, db: Session = Depends(get_db)):
    rule = activate_pricing_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule
