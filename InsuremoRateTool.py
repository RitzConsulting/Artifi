#!/usr/bin/env python3
"""
Blueprint-Compliant InsureMO Rate Tool
Commercial Insurance Premium Rating via InsureMO API

This tool provides simplified premium rating for commercial insurance policies
through the InsureMO platform, following the Blueprint framework standards.

Design Principles:
- Blueprint-compliant structure with proper inheritance from BaseTool
- Comprehensive error handling and logging
- Support for both standalone and integrated usage
- Structured input/output schemas for agent compatibility
"""

import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

# Blueprint Base Tool Import Pattern
try:
    from Blueprint.Templates.Tools.python_base_tool import BaseTool
except ImportError:
    # Fallback for testing/development
    class BaseTool:
        """Mock BaseTool for standalone testing."""
        def __init__(self):
            pass
        def run_sync(self, **kwargs):
            raise NotImplementedError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InsuremoRateTool(BaseTool):
    """
    Blueprint-compliant tool for commercial insurance premium rating via InsureMO API.
    
    This tool handles the complete rating workflow:
    1. Creates a policy with provided business information
    2. Calculates premium based on risk factors
    3. Returns comprehensive rating results
    """
    
    # REQUIRED STUDIO METADATA
    name = "InsuremoRateTool"
    description = "Commercial insurance premium rating via InsureMO API. Creates policies and calculates premiums for general liability and property coverage."
    version = "3.0.0"
    
    # Environment variables required
    requires_env_vars = [
        "INSUREMO_API_TOKEN: Bearer token for InsureMO API authentication",
        "INSUREMO_BASE_URL: Base URL for InsureMO API (e.g., https://ebaogi-gi-sandbox-am.insuremo.com)"
    ]
    
    # Dependencies
    dependencies = [
        ("requests", "requests"),
        ("urllib3", "urllib3")
    ]
    
    # Tool configuration
    uses_llm = False
    default_llm_model = None
    default_system_instructions = None
    structured_output = True
    direct_to_user = False
    respond_back_to_agent = True
    response_type = "json"
    call_back_url = None
    
    # INPUT SCHEMA
    input_schema = {
        "type": "object",
        "properties": {
            "customerName": {
                "type": "string",
                "description": "Business name for the policy",
                "examples": ["Sweet Dreams Bakery LLC", "TechParts Manufacturing Inc"]
            },
            "address1": {
                "type": "string",
                "description": "Primary address line",
                "examples": ["123 Main Street", "456 Industrial Blvd"]
            },
            "city": {
                "type": "string",
                "description": "City name",
                "examples": ["Houston", "Dallas", "Austin"]
            },
            "state": {
                "type": "string",
                "description": "State code (2 letters)",
                "examples": ["TX", "CA", "NY"],
                "pattern": "^[A-Z]{2}$"
            },
            "zipCode": {
                "type": "string",
                "description": "ZIP code",
                "examples": ["77001", "75201"],
                "pattern": "^\\d{5}(-\\d{4})?$"
            },
            "businessType": {
                "type": "string",
                "description": "Type of business",
                "enum": ["Retail", "Wholesale", "Manufacturing", "Service"],
                "default": "Retail"
            },
            "naicsCode": {
                "type": "string",
                "description": "NAICS industry code",
                "examples": ["311811", "333316"],
                "default": "311811"
            },
            "naicsDefinition": {
                "type": "string",
                "description": "NAICS code description",
                "examples": ["Retail Bakeries", "Photographic Equipment Manufacturing"],
                "default": "Retail Bakeries"
            },
            "legalStructure": {
                "type": "string",
                "description": "Legal structure of business",
                "enum": ["LLC", "Corporation", "Partnership", "SoleProprietorship"],
                "default": "LLC"
            },
            "fullTimeEmpl": {
                "type": "integer",
                "description": "Number of full-time employees",
                "minimum": 0,
                "default": 5
            },
            "partTimeEmpl": {
                "type": "integer",
                "description": "Number of part-time employees",
                "minimum": 0,
                "default": 0
            },
            "buildingLimit": {
                "type": "integer",
                "description": "Building coverage limit in dollars",
                "minimum": 0,
                "default": 500000
            },
            "bppLimit": {
                "type": "integer",
                "description": "Business personal property limit in dollars",
                "minimum": 0,
                "default": 100000
            },
            "eachOccurrenceLimit": {
                "type": "string",
                "description": "Each occurrence liability limit",
                "enum": ["1,000,000 CSL", "2,000,000 CSL", "5,000,000 CSL"],
                "default": "1,000,000 CSL"
            },
            "generalAggregateLimit": {
                "type": "string",
                "description": "General aggregate liability limit",
                "enum": ["2,000,000 CSL", "4,000,000 CSL", "10,000,000 CSL"],
                "default": "2,000,000 CSL"
            },
            "api_token": {
                "type": "string",
                "description": "Override API token (optional - uses env var if not provided)"
            },
            "base_url": {
                "type": "string",
                "description": "Override base URL (optional - uses env var if not provided)"
            }
        },
        "required": ["customerName", "address1", "city", "state", "zipCode"]
    }
    
    # OUTPUT SCHEMA
    output_schema = {
        "type": "object",
        "properties": {
            "success": {
                "type": "boolean",
                "description": "Whether the rating was successful"
            },
            "proposalNo": {
                "type": "string",
                "description": "Generated proposal number"
            },
            "policyId": {
                "type": ["integer", "null"],
                "description": "Policy ID from the system"
            },
            "totalPremium": {
                "type": "number",
                "description": "Total calculated premium"
            },
            "grossPremium": {
                "type": "number",
                "description": "Gross premium amount"
            },
            "commission": {
                "type": "number",
                "description": "Commission amount"
            },
            "commissionRate": {
                "type": "number",
                "description": "Commission rate as decimal"
            },
            "glPremium": {
                "type": "number",
                "description": "General liability premium"
            },
            "propertyPremium": {
                "type": "number",
                "description": "Property coverage premium"
            },
            "effectiveDate": {
                "type": "string",
                "description": "Policy effective date"
            },
            "expiryDate": {
                "type": "string",
                "description": "Policy expiry date"
            },
            "premiumBreakdown": {
                "type": "object",
                "description": "Detailed premium breakdown"
            },
            "error": {
                "type": "string",
                "description": "Error message if rating failed"
            },
            "errorDetails": {
                "type": "object",
                "description": "Additional error information"
            }
        },
        "required": ["success"]
    }
    
    # STUDIO CONFIGURATION
    config = {
        "timeout_seconds": 30,
        "max_retries": 3,
        "backoff_factor": 1
    }
    
    # API ENDPOINTS
    ENDPOINTS = {
        "create": "/api/ebaogi/api-orchestration/v1/flow/easypa_createOrSave",
        "calculate": "/api/ebaogi/api-orchestration/v1/flow/easypa_calculate",
        "bind": "/api/ebaogi/api-orchestration/v1/flow/easypa_bind",
        "issue": "/api/ebaogi/api-orchestration/v1/flow/easypa_issue",
        "load": "/api/platform/proposal/v1/load"
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the InsureMO Rate Tool.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__()
        
        # Override config if provided
        if config:
            self.config.update(config)
        
        self.api_token = None
        self.base_url = None
        self.session = None
        self._initialized = False
        
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self._cleanup()
        
    def __del__(self):
        """Destructor with cleanup."""
        self._cleanup()
        
    def _cleanup(self):
        """Clean up resources."""
        if self.session:
            try:
                self.session.close()
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
            finally:
                self.session = None
                self._initialized = False
    
    def _initialize(self, api_token: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize API connection and session.
        
        Args:
            api_token: Optional API token override
            base_url: Optional base URL override
        """
        if self._initialized:
            return
        
        # Get credentials
        self.api_token = api_token or os.getenv("INSUREMO_API_TOKEN")
        self.base_url = base_url or os.getenv("INSUREMO_BASE_URL")
        
        if not self.api_token:
            raise ValueError("API token required. Provide as parameter or set INSUREMO_API_TOKEN")
        if not self.base_url:
            raise ValueError("Base URL required. Provide as parameter or set INSUREMO_BASE_URL")
        
        # Create session
        self.session = self._create_session()
        self._initialized = True
        
        logger.info(f"InsureMO Rate Tool initialized for {self.base_url}")
    
    def _create_session(self):
        """Create a requests session with retry logic."""
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
        except ImportError:
            raise ImportError("requests package required. Install with: pip install requests")
        
        session = requests.Session()
        
        # Create retry strategy with compatibility for different urllib3 versions
        retry_kwargs = {
            'total': self.config['max_retries'],
            'status_forcelist': [429, 500, 502, 503, 504],
            'backoff_factor': self.config['backoff_factor']
        }
        
        # Try new parameter name first (urllib3 >= 1.26)
        try:
            retry_kwargs['allowed_methods'] = ["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
            retry_strategy = Retry(**retry_kwargs)
        except TypeError:
            # Fall back to old parameter name (urllib3 < 1.26)
            del retry_kwargs['allowed_methods']
            retry_kwargs['method_whitelist'] = ["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
            retry_strategy = Retry(**retry_kwargs)
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"{self.name}/{self.version}"
        })
        
        return session
    
    def run_sync(self, **kwargs) -> Dict[str, Any]:
        """
        Main execution method for premium rating.
        
        Args:
            **kwargs: Parameters matching the input_schema
            
        Returns:
            Dict matching the output_schema
        """
        try:
            # Extract API credentials if provided
            api_token = kwargs.pop("api_token", None)
            base_url = kwargs.pop("base_url", None)
            
            # Initialize if needed
            self._initialize(api_token, base_url)
            
            # Validate required fields
            required_fields = ["customerName", "address1", "city", "state", "zipCode"]
            missing_fields = [f for f in required_fields if not kwargs.get(f)]
            if missing_fields:
                return self._create_error_response(f"Missing required fields: {', '.join(missing_fields)}")
            
            # Step 1: Create policy
            logger.info(f"Creating policy for {kwargs.get('customerName')}")
            created_data = self._create_policy(**kwargs)
            if not created_data:
                return self._create_error_response("Failed to create policy")
            
            proposal_no = created_data.get("ProposalNo")
            if not proposal_no:
                return self._create_error_response("No proposal number returned from create API")
            
            logger.info(f"Policy created with proposal number: {proposal_no}")
            
            # Step 2: Calculate premium
            logger.info("Calculating premium...")
            calculated_data = self._calculate_premium(created_data)
            if not calculated_data:
                return self._create_error_response("Failed to calculate premium")
            
            # Extract and return results
            return self._create_success_response(calculated_data)
            
        except Exception as e:
            logger.error(f"Rate tool execution failed: {str(e)}", exc_info=True)
            return self._create_error_response(str(e))
        finally:
            self._cleanup()
    
    def _create_policy(self, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Create a policy with the InsureMO API.
        
        Args:
            **kwargs: Business information for the policy
            
        Returns:
            Created policy data or None if failed
        """
        try:
            payload = self._build_policy_payload(**kwargs)
            url = f"{self.base_url}{self.ENDPOINTS['create']}"
            
            response = self.session.post(
                url, 
                json=payload, 
                timeout=self.config['timeout_seconds']
            )
            
            if response.status_code != 200:
                logger.error(f"Create API returned status {response.status_code}: {response.text}")
                return None
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error creating policy: {str(e)}")
            return None
    
    def _calculate_premium(self, policy_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Calculate premium for a created policy.
        
        Args:
            policy_data: The policy data from create API
            
        Returns:
            Calculated policy data or None if failed
        """
        try:
            url = f"{self.base_url}{self.ENDPOINTS['calculate']}"
            
            response = self.session.post(
                url, 
                json=policy_data, 
                timeout=self.config['timeout_seconds']
            )
            
            if response.status_code != 200:
                logger.error(f"Calculate API returned status {response.status_code}: {response.text}")
                return None
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error calculating premium: {str(e)}")
            return None
    
    def _build_policy_payload(self, **kwargs) -> Dict[str, Any]:
        """
        Build the complete policy payload with defaults.
        
        Args:
            **kwargs: Business information
            
        Returns:
            Complete policy payload for API
        """
        dates = self._get_default_dates()
        
        # Build payload - using same structure as original tool
        payload = {
            "ProductCode": "X_CO_US_USCGLPP8",
            "ProductVersion": "20240801_V01",
            "OrgCode": "10001",
            "AgentCode": "PTY10000039468001",
            "PremiumCurrencyCode": "USD",
            "BookCurrencyCode": "USD",
            "PremiumBookExchangeRate": 1,
            "LocalCurrencyCode": "USD",
            "PremiumLocalExchangeRate": 1,
            "ProposalDate": dates["proposalDate"],
            "EffectiveDate": dates["effectiveDate"],
            "ExpiryDate": dates["expiryDate"],
            
            "PolicyCustomerList": [{
                "CustomerName": kwargs.get("customerName", ""),
                "CustomerNo": kwargs.get("customerNo", "CO00000001"),
                "DateOfBirth": dates["dateOfBirth"],
                "IdNo": kwargs.get("idNo", "01010101"),
                "IdType": "4",
                "IsOrgParty": "N",
                "PolicyStatus": 2,
                "PostCode": kwargs.get("postCode", kwargs.get("zipCode", "")),
                "CustomerType": "OrgCustomer",
                "State": kwargs.get("state", ""),
                "IsPolicyHolder": "Y"
            }],
            
            "PolicyPaymentInfoList": [{
                "PayModeCode": 100,
                "IsInstallment": "N",
                "InstallmentType": "10",
                "BillingType": "1"
            }],
            
            "PolicyLobList": [self._build_lob_section(**kwargs)]
        }
        
        return payload
    
    def _build_lob_section(self, **kwargs) -> Dict[str, Any]:
        """Build the Line of Business section of the payload."""
        return {
            "XCGLIncluded": "Yes",
            "XCFIncluded": "Yes",
            "XEachOccurrenceLimit": kwargs.get("eachOccurrenceLimit", "1,000,000 CSL"),
            "XGeneralAggregateLimit": kwargs.get("generalAggregateLimit", "2,000,000 CSL"),
            "XPersonalAdvertisingInjuryLimit": "1000000",
            "XDamageToRentedPremisesLimit": "100000",
            "XMedicalExpenseLimit": "5000",
            "XProdsCompldOpsAggregateLimit": kwargs.get("generalAggregateLimit", "2,000,000 CSL"),
            "XBIDeductibles": "1,000 Per Occurrence",
            "XPDDeductibles": "1,000 Per Occurrence",
            
            # Risk questions (all defaulted to "No")
            "XMedicalFacilitiesOrProfessionals": "No",
            "XExposureToRadioactiveMaterials": "No",
            "XOperationsInvolvingHazardousMaterial": "No",
            "XOperationsSoldAcquiredDiscontinued5Years": "No",
            "XMachineryEquipmentLoanedOrRented": "No",
            "XWatercraftDocksFloatsOwnedHiredLeased": "No",
            "XParkingFacilitiesOwnedRented": "No",
            "XFeeChargedForParking": "No",
            "XRecreationFacilitiesProvided": "No",
            "XSwimmingPoolOnPremises": "No",
            "XSportingSocialEventsSponsored": "No",
            "XStructuralAlterationsContemplated": "No",
            "XDemolitionExposureContemplated": "No",
            "XActiveInJointVentures": "No",
            "XLeaseEmployeesToFromOtherEmployers": "No",
            "XLaborInterchangeWithOtherBusinesses": "No",
            "XDayCareFacilitiesOperatedControlled": "No",
            "XCrimesOccurredOnPremisesLast3Years": "No",
            "XWrittenSafetySecurityPolicyInEffect": "No",
            "XPromotionalLiteratureSafetySecurity": "No",
            "XLossHistorySumaryHeader": "No",
            "XLossHistoryYears": 3,
            
            # Premium fields
            "XCalculatedTotalPremium": 0,
            "XPremium": 0,
            "XPolicyTermPremium": 0,
            "XFinalPremium": 0,
            
            # Business information
            "XSIC": "5461",
            "XNAICSCode": kwargs.get("naicsCode", "311811"),
            "XNAICSDefinition": kwargs.get("naicsDefinition", "Retail Bakeries"),
            "XLegalStructure": kwargs.get("legalStructure", "LLC"),
            "XLLCNumOfMembersManagers": 2,
            "XBusinessType": kwargs.get("businessType", "Retail"),
            "XDateStarted": self._get_default_dates()["dateStarted"],
            "XPrimaryOperations": "",
            "XRetailPct": 100,
            
            # Location and risk information
            "PolicyRiskList": [self._build_risk_section(**kwargs)],
            
            "ProductCode": "X_CO_US_USCGLPP8",
            "ProductElementCode": "X_CO_US_USCGLPP8"
        }
    
    def _build_risk_section(self, **kwargs) -> Dict[str, Any]:
        """Build the risk section of the payload."""
        return {
            "XUnitNumber": 1,
            "XAnyAreaLeasedToOthers": "No",
            "XProtectionClass": "5",
            "XGLPremium": 0,
            "XCFPremium": 0,
            "XCalculatedTotalPremium": 0,
            "XPremium": 0,
            "XPolicyTermPremium": 0,
            "XAddress1": kwargs.get("address1", ""),
            "XCity": kwargs.get("city", ""),
            "XAddress2": "",
            "XCounty": "",
            "XState": kwargs.get("state", ""),
            "XZipCode": kwargs.get("zipCode", ""),
            "XCityLimits": "Inside",
            "XLocInterest": "Owner",
            "XFullTimeEmpl": int(kwargs.get("fullTimeEmpl", 5)),
            "XPartTimeEmpl": int(kwargs.get("partTimeEmpl", 0)),
            
            "PolicyRiskList": [
                self._build_gl_classification(),
                self._build_building_coverage(**kwargs)
            ],
            
            "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATION"
        }
    
    def _build_gl_classification(self) -> Dict[str, Any]:
        """Build GL classification section."""
        return {
            "XClassCode": "10100",
            "XClassDescription": "Bakeries",
            "PolicyCoverageList": [
                {
                    "XInstallServiceDemonstrateProducts": "No",
                    "XForeignProductsSoldDistributedUsed": "No",
                    "XResearchDevelopmentNewProducts": "No",
                    "XGuaranteesWarrantiesHoldHarmless": "No",
                    "XProductsAircraftSpaceIndustry": "No",
                    "XProductsRecalledDiscontinuedChanged": "No",
                    "XProductsOthersSoldRepackaged": "No",
                    "XProductsUnderLabelOfOthers": "No",
                    "XVendorsCoverageRequired": "No",
                    "XNamedInsuredSellToOtherInsureds": "No",
                    "XProdsCompldOpsPremiumBasis": "Gross Sales",
                    "XProdsCompldOpsCovExposure": 1000000,
                    "XProdsCompldOpsRate": 0.12,
                    "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATIONCLASSIFICATIONPRODSCOMPLDOPSCOVERAGE"
                },
                {
                    "XPremOpsPremiumBasis": "Gross Sales",
                    "XPremOpsExposure": 1000000,
                    "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATIONCLASSIFICATIONPREMOPSCOVERAGE"
                }
            ],
            "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATIONGLCLASSIFICATION"
        }
    
    def _build_building_coverage(self, **kwargs) -> Dict[str, Any]:
        """Build building coverage section."""
        return {
            "XUnitNumber": 1,
            "XDesignatedAsHistoricalLandmark": "No",
            "XBldgImpWiring": "No",
            "XBldgImpPlumbing": "No",
            "XBldgImpRoofing": "No",
            "XBldgImpHeating": "No",
            "XWindClass": "NA",
            "XSolidFuelHeater": "No",
            "XBurglarAlarmCentralStation": "No",
            "XBurglarAlarmLocalGong": "No",
            "XGuardsClockFreq": "Hourly",
            "XFireAlarmCentralStation": "No",
            "XFireAlarmLocalGong": "No",
            "XBldgDescription": "Commercial Building",
            "XOpenSides": 0,
            "XConstructionType": "FireResistive",
            "XNumberOfStories": 1,
            "XYearBuilt": 2010,
            "XTotalArea": 5000,
            "XBCEG": 2,
            "PolicyCoverageList": [
                {
                    "XCoverageOnPolicyIndicator": 1,
                    "XBldgCovCoins": "80",
                    "XBldgCovValuation": "A",
                    "XBldgCovCauseOfLoss": "Special",
                    "XBldgCovInflationGuard": 5,
                    "XBldgCovDeductible": 500,
                    "XBldgCovLimit": int(kwargs.get("buildingLimit", 500000)),
                    "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATIONCFBUILDINGBUILDINGCOVERAGE"
                },
                {
                    "XCoverageOnPolicyIndicator": 1,
                    "XPersonalProperty": "Yes",
                    "XPropertyOfOthers": "Yes",
                    "XStock": "No",
                    "XFixturesFurnitures": "No",
                    "XMachineryEquipment": "No",
                    "XBPPCovCoins": "80",
                    "XBPPCovValuation": "A",
                    "XBPPCovCauseOfLoss": "Special",
                    "XBPPCovInflationGuard": 5,
                    "XBPPCovDeductible": 500,
                    "XBPPCovLimit": int(kwargs.get("bppLimit", 100000)),
                    "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATIONCFBUILDINGBPPCOVERAGE"
                },
                {
                    "XCoverageOnPolicyIndicator": 1,
                    "XBICCoverage": "BusinessIncomeWithExtraExpense",
                    "XBICCovCoins": "80",
                    "XBICCovCauseOfLoss": "Special",
                    "XWaitingPeriodDays": 3,
                    "XBICOrdinaryPayrollExcluded": "No",
                    "XBICOrdinaryPayrollLimitation": "90Days",
                    "XBICExtendedPeriodOfIndemnity": "No",
                    "XBICMonthlyPeriodOfIndemnity": "No",
                    "XBICMaximumPeriodOfIndemnity": "No",
                    "XBICPowerHeatDed": "No",
                    "XBICEMediaRec": "No",
                    "XBIEOrdOrLaw": "No",
                    "XBICCivilAuth": "No",
                    "XBICOffPremSrvInt": "No",
                    "XBICDependProp": "No",
                    "XBICCovLimit": 200000,
                    "XBICTypeOfBusiness": "NonManufacturing",
                    "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATIONCFBUILDINGBIC"
                },
                {
                    "XCoverageOnPolicyIndicator": 0,
                    "XSCDeductible": 500,
                    "XSCRefrigMaintAgreement": "No",
                    "XSCBreakdownOrContamination": "No",
                    "XSCPowerOutage": "No",
                    "XSCSellingPrice": "No",
                    "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATIONCFBUILDINGSPOILAGECOVERAGE"
                }
            ],
            "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATIONCFBUILDING"
        }
    
    def _get_default_dates(self) -> Dict[str, str]:
        """Get default dates for policy."""
        today = datetime.now()
        return {
            "proposalDate": today.strftime("%Y-%m-%d"),
            "effectiveDate": today.strftime("%Y-%m-%d"),
            "expiryDate": (today + timedelta(days=365)).strftime("%Y-%m-%d"),
            "dateStarted": (today - timedelta(days=730)).strftime("%Y-%m-%d"),
            "dateOfBirth": (today - timedelta(days=730)).strftime("%Y-%m-%d")
        }
    
    def _extract_premium_breakdown(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract detailed premium breakdown from policy data."""
        breakdown = {
            "totalPremium": policy_data.get("TotalPremium", 0),
            "grossPremium": policy_data.get("GrossPremium", 0),
            "glPremium": 0,
            "propertyPremium": 0,
            "buildingPremium": 0,
            "bppPremium": 0,
            "biPremium": 0
        }
        
        try:
            lob_list = policy_data.get("PolicyLobList", [])
            if lob_list:
                risk_list = lob_list[0].get("PolicyRiskList", [])
                if risk_list:
                    location = risk_list[0]
                    breakdown["glPremium"] = location.get("XGLPremium", 0)
                    breakdown["propertyPremium"] = location.get("XCFPremium", 0)
        except Exception as e:
            logger.warning(f"Could not extract detailed premium breakdown: {str(e)}")
        
        return breakdown
    
    def _create_success_response(self, calculated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create standardized success response."""
        premium_breakdown = self._extract_premium_breakdown(calculated_data)
        
        return {
            "success": True,
            "proposalNo": calculated_data.get("ProposalNo"),
            "policyId": calculated_data.get("PolicyId"),
            "totalPremium": calculated_data.get("TotalPremium", 0),
            "grossPremium": calculated_data.get("GrossPremium", 0),
            "commission": calculated_data.get("Commission", 0),
            "commissionRate": calculated_data.get("CommissionRate", 0),
            "glPremium": premium_breakdown["glPremium"],
            "propertyPremium": premium_breakdown["propertyPremium"],
            "effectiveDate": calculated_data.get("EffectiveDate"),
            "expiryDate": calculated_data.get("ExpiryDate"),
            "premiumBreakdown": premium_breakdown
        }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response."""
        logger.error(error_message)
        return {
            "success": False,
            "error": error_message,
            "errorDetails": {
                "type": "ProcessingError",
                "message": error_message
            }
        }


# PLATFORM INTEGRATION FUNCTION
def execute_tool(**kwargs) -> Dict[str, Any]:
    """
    Execute the InsureMO Rate Tool for platform integration.
    
    This is the standard entry point for the Blueprint framework.
    
    Args:
        **kwargs: Tool input parameters matching the input_schema
        
    Returns:
        Dict containing rating results matching the output_schema
    """
    with InsuremoRateTool() as tool:
        return tool.run_sync(**kwargs)


# METADATA EXPORT AND TESTING
if __name__ == "__main__":
    # Export tool metadata for platform registration
    tool_metadata = {
        "class_name": "InsuremoRateTool",
        "name": InsuremoRateTool.name,
        "description": InsuremoRateTool.description,
        "version": InsuremoRateTool.version,
        "requires_env_vars": InsuremoRateTool.requires_env_vars,
        "dependencies": InsuremoRateTool.dependencies,
        "uses_llm": InsuremoRateTool.uses_llm,
        "structured_output": InsuremoRateTool.structured_output,
        "input_schema": InsuremoRateTool.input_schema,
        "output_schema": InsuremoRateTool.output_schema,
        "response_type": InsuremoRateTool.response_type,
        "direct_to_user": InsuremoRateTool.direct_to_user,
        "respond_back_to_agent": InsuremoRateTool.respond_back_to_agent
    }
    
    print("\n" + "="*80)
    print(" InsureMO Rate Tool - Blueprint-Compliant Commercial Insurance Rating")
    print("="*80)
    print(f" Version: {InsuremoRateTool.version}")
    print(f" Framework: Blueprint-Compliant with BaseTool inheritance")
    print("-"*80)
    
    print("\n📋 Tool Metadata:")
    print(json.dumps(tool_metadata, indent=2))
    
    print("\n" + "-"*80)
    print(" Testing the tool...")
    print("-"*80)
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Small Retail Bakery",
            "data": {
                "customerName": "Sweet Dreams Bakery LLC",
                "address1": "123 Main Street",
                "city": "Houston",
                "state": "TX",
                "zipCode": "77001",
                "businessType": "Retail",
                "naicsCode": "311811",
                "naicsDefinition": "Retail Bakeries",
                "fullTimeEmpl": 5,
                "partTimeEmpl": 2,
                "buildingLimit": 500000,
                "bppLimit": 100000
            }
        },
        {
            "name": "Manufacturing Facility",
            "data": {
                "customerName": "TechParts Manufacturing Inc",
                "address1": "456 Industrial Blvd",
                "city": "Dallas",
                "state": "TX",
                "zipCode": "75201",
                "businessType": "Manufacturing",
                "naicsCode": "333316",
                "naicsDefinition": "Photographic Equipment Manufacturing",
                "fullTimeEmpl": 25,
                "partTimeEmpl": 5,
                "buildingLimit": 1500000,
                "bppLimit": 800000,
                "eachOccurrenceLimit": "2,000,000 CSL",
                "generalAggregateLimit": "4,000,000 CSL"
            }
        },
        {
            "name": "Service Company",
            "data": {
                "customerName": "Professional Services Corp",
                "address1": "789 Business Park",
                "city": "Austin",
                "state": "TX",
                "zipCode": "78701",
                "businessType": "Service",
                "naicsCode": "541511",
                "naicsDefinition": "Custom Computer Programming Services",
                "fullTimeEmpl": 15,
                "partTimeEmpl": 3,
                "buildingLimit": 250000,
                "bppLimit": 150000,
                "legalStructure": "Corporation"
            }
        }
    ]
    
    # Check and set environment variables if not present
    if not os.getenv("INSUREMO_API_TOKEN"):
        print("\n⚠️  Warning: INSUREMO_API_TOKEN not set in environment")
        print("   Setting default token for testing...")
        os.environ["INSUREMO_API_TOKEN"] = "MOATnRGmthYVAX1Dcrcve-WV8PEa0nds"
    
    if not os.getenv("INSUREMO_BASE_URL"):
        print("⚠️  Warning: INSUREMO_BASE_URL not set in environment")
        print("   Setting default URL for testing...")
        os.environ["INSUREMO_BASE_URL"] = "https://ebaogi-gi-sandbox-am.insuremo.com"
    
    # Run test scenarios
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*80}")
        print(f" Test Scenario {i}: {scenario['name']}")
        print(f"{'='*80}")
        
        test_data = scenario['data']
        print(f"\nBusiness: {test_data['customerName']}")
        print(f"Location: {test_data['address1']}, {test_data['city']}, {test_data['state']} {test_data['zipCode']}")
        print(f"Type: {test_data['businessType']}")
        print(f"Employees: {test_data['fullTimeEmpl']} FT, {test_data.get('partTimeEmpl', 0)} PT")
        print(f"Building Limit: ${test_data.get('buildingLimit', 500000):,}")
        print(f"BPP Limit: ${test_data.get('bppLimit', 100000):,}")
        
        print("\n" + "-"*40)
        print(" Executing Rating...")
        print("-"*40)
        
        try:
            # Execute the tool
            result = execute_tool(**test_data)
            
            if result["success"]:
                print("\n✅ Rating Successful!")
                print(f"\n📋 Proposal Number: {result.get('proposalNo')}")
                print(f"📄 Policy ID: {result.get('policyId')}")
                
                print(f"\n💰 Premium Summary:")
                print(f"   Total Premium:    ${result.get('totalPremium', 0):>12,.2f}")
                print(f"   GL Premium:       ${result.get('glPremium', 0):>12,.2f}")
                print(f"   Property Premium: ${result.get('propertyPremium', 0):>12,.2f}")
                
                commission = result.get('commission', 0)
                commission_rate = result.get('commissionRate', 0)
                if commission > 0:
                    print(f"   Commission:       ${commission:>12,.2f} ({commission_rate*100:.1f}%)")
                
                print(f"\n📅 Policy Term:")
                print(f"   Effective Date: {result.get('effectiveDate')}")
                print(f"   Expiry Date:    {result.get('expiryDate')}")
                
                # Save result to file
                filename = f"quote_{i}_{test_data['customerName'].replace(' ', '_').replace('.', '')}.json"
                with open(filename, "w") as f:
                    json.dump(result, f, indent=2)
                print(f"\n💾 Results saved to: {filename}")
                
            else:
                print(f"\n❌ Rating Failed:")
                error_details = result.get('errorDetails', {})
                print(f"   Error Type: {error_details.get('type', 'Unknown')}")
                print(f"   Error: {result.get('error')}")
                if error_details.get('message'):
                    print(f"   Details: {error_details['message']}")
                
        except Exception as e:
            print(f"\n❌ Test failed with exception:")
            print(f"   {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Brief pause between scenarios
        if i < len(test_scenarios):
            time.sleep(2)
    
    print("\n" + "="*80)
    print(" Testing Complete")
    print("="*80)
    
    # Display usage examples
    print("\n📚 Usage Examples:")
    print("-"*40)
    
    print("\n1. As a Blueprint Tool (Platform Integration):")
    print("""
    result = execute_tool(
        customerName="Your Business LLC",
        address1="123 Main St",
        city="Houston",
        state="TX",
        zipCode="77001",
        businessType="Retail",
        fullTimeEmpl=10,
        buildingLimit=750000,
        bppLimit=250000
    )
    """)
    
    print("\n2. Direct Class Usage:")
    print("""
    with InsuremoRateTool() as tool:
        result = tool.run_sync(
            customerName="Your Business",
            address1="456 Oak Ave",
            city="Dallas",
            state="TX",
            zipCode="75201"
        )
    """)
    
    print("\n3. With Custom Credentials:")
    print("""
    result = execute_tool(
        customerName="Test Corp",
        address1="789 Pine St",
        city="Austin",
        state="TX",
        zipCode="78701",
        api_token="YOUR_API_TOKEN",
        base_url="YOUR_BASE_URL"
    )
    """)
    
    print("\n" + "="*80)
    print(" Blueprint-Compliant InsureMO Rate Tool Ready for Deployment")
    print("="*80)