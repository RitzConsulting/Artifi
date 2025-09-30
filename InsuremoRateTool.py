#!/usr/bin/env python3
"""
Blueprint-Compliant InsureMO Rate Tool - Agent-Optimized Version
Commercial Insurance Premium Rating via InsureMO API

This tool provides simplified premium rating for commercial insurance policies
through the InsureMO platform, optimized for AI Agent integration.

Key Modifications:
- Enhanced JSON input validation and parsing
- Improved error messages for agent consumption
- Added input sanitization for agent-provided data
- Streamlined response format for agent summarization
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
    Agent-Optimized InsureMO Premium Rating Tool.
    
    Designed for seamless AI Agent integration with:
    - Robust JSON input parsing from agents
    - Clear, structured responses for agent summarization
    - Enhanced error handling with agent-friendly messages
    """
    
    # REQUIRED STUDIO METADATA
    name = "InsuremoRateTool"
    description = "Commercial insurance premium rating via InsureMO API. Creates policies and calculates premiums for general liability and property coverage."
    version = "3.1.0"
    
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
    
    # Tool configuration - Optimized for Agent interaction
    uses_llm = False
    default_llm_model = None
    default_system_instructions = None
    structured_output = True
    direct_to_user = False
    respond_back_to_agent = True  # Key setting for agent response
    response_type = "json"
    call_back_url = None
    
    # INPUT SCHEMA - Agent-friendly with clear descriptions
    input_schema = {
        "type": "object",
        "properties": {
            "customerName": {
                "type": "string",
                "description": "Business name for the policy"
            },
            "address1": {
                "type": "string",
                "description": "Primary address line"
            },
            "city": {
                "type": "string",
                "description": "City name"
            },
            "state": {
                "type": "string",
                "description": "State code (2 letters, e.g., CA, TX)",
                "pattern": "^[A-Z]{2}$"
            },
            "zipCode": {
                "type": "string",
                "description": "ZIP code (5 or 9 digits)",
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
                "default": "311811"
            },
            "naicsDefinition": {
                "type": "string",
                "description": "NAICS code description",
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
            }
        },
        "required": ["customerName", "address1", "city", "state", "zipCode"],
        "additionalProperties": True
    }
    
    # OUTPUT SCHEMA - Streamlined for agent summarization
    output_schema = {
        "type": "object",
        "properties": {
            "success": {
                "type": "boolean",
                "description": "Whether the rating was successful"
            },
            "summary": {
                "type": ["string", "null"],
                "description": "Human-readable summary for the agent"
            },
            "proposalNo": {
                "type": ["string", "null"],
                "description": "Generated proposal number"
            },
            "policyId": {
                "type": ["integer", "null"],
                "description": "Policy ID from the system"
            },
            "premiums": {
                "type": ["object", "null"],
                "properties": {
                    "total": {"type": "number"},
                    "gross": {"type": "number"},
                    "generalLiability": {"type": "number"},
                    "property": {"type": "number"},
                    "commission": {"type": "number"},
                    "commissionRate": {"type": "number"}
                }
            },
            "coverage": {
                "type": ["object", "null"],
                "properties": {
                    "effectiveDate": {"type": "string"},
                    "expiryDate": {"type": "string"},
                    "term": {"type": "string"}
                }
            },
            "error": {
                "type": ["string", "null"],
                "description": "Error message if rating failed"
            },
            "agentInstructions": {
                "type": ["string", "null"],
                "description": "Instructions for the agent on how to use the response"
            }
        },
        "required": ["success"],
        "additionalProperties": True
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
    
    # Default values for optional parameters
    DEFAULT_VALUES = {
        "businessType": "Retail",
        "naicsCode": "311811",
        "naicsDefinition": "Retail Bakeries",
        "legalStructure": "LLC",
        "fullTimeEmpl": 5,
        "partTimeEmpl": 0,
        "buildingLimit": 500000,
        "bppLimit": 100000,
        "eachOccurrenceLimit": "1,000,000 CSL",
        "generalAggregateLimit": "2,000,000 CSL"
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the InsureMO Rate Tool."""
        super().__init__()
        
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
        """Initialize API connection and session."""
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
        
        # Create retry strategy
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
    
    def parse_agent_input(self, input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse and validate input from AI Agent.
        
        Args:
            input_data: JSON string or dict from agent
            
        Returns:
            Validated and normalized input dict
        """
        # Handle JSON string input
        if isinstance(input_data, str):
            try:
                input_data = json.loads(input_data)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON input from agent: {e}")
                raise ValueError(f"Invalid JSON format: {e}")
        
        # Sanitize and normalize input
        sanitized = {}
        for key, value in input_data.items():
            # Remove any leading/trailing whitespace from strings
            if isinstance(value, str):
                value = value.strip()
            
            # Normalize state codes to uppercase
            if key == "state" and isinstance(value, str):
                value = value.upper()
            
            # Ensure employee counts are integers
            if key in ["fullTimeEmpl", "partTimeEmpl"] and value is not None:
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid {key} value: {value}, using default")
                    value = self.DEFAULT_VALUES.get(key, 0)
            
            # Ensure coverage limits are integers
            if key in ["buildingLimit", "bppLimit"] and value is not None:
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid {key} value: {value}, using default")
                    value = self.DEFAULT_VALUES.get(key, 0)
            
            sanitized[key] = value
        
        return sanitized
    
    def run_sync(self, **kwargs) -> Dict[str, Any]:
        """
        Main execution method for premium rating - Agent optimized.
        
        Args:
            **kwargs: Parameters from AI Agent (can include raw JSON)
            
        Returns:
            Agent-friendly JSON response with summary and structured data
        """
        try:
            # Handle direct JSON input from agent
            if "input" in kwargs and isinstance(kwargs["input"], (str, dict)):
                params = self.parse_agent_input(kwargs["input"])
            else:
                params = self.parse_agent_input(kwargs)
            
            # Apply default values for missing optional parameters
            params = self._apply_defaults(params)
            
            # Extract API credentials if provided
            api_token = params.pop("api_token", None)
            base_url = params.pop("base_url", None)
            
            # Initialize if needed
            self._initialize(api_token, base_url)
            
            # Validate required fields
            required_fields = ["customerName", "address1", "city", "state", "zipCode"]
            missing_fields = [f for f in required_fields if not params.get(f)]
            if missing_fields:
                return self._create_agent_error_response(
                    f"Missing required fields: {', '.join(missing_fields)}",
                    missing_fields
                )
            
            # Step 1: Create policy
            logger.info(f"Creating policy for {params.get('customerName')}")
            created_data = self._create_policy(**params)
            if not created_data:
                return self._create_agent_error_response(
                    "Failed to create policy in InsureMO system",
                    context="Policy creation step"
                )
            
            proposal_no = created_data.get("ProposalNo")
            if not proposal_no:
                return self._create_agent_error_response(
                    "No proposal number returned from InsureMO",
                    context="Policy creation response"
                )
            
            logger.info(f"Policy created with proposal number: {proposal_no}")
            
            # Step 2: Calculate premium
            logger.info("Calculating premium...")
            calculated_data = self._calculate_premium(created_data)
            if not calculated_data:
                return self._create_agent_error_response(
                    "Failed to calculate premium",
                    context="Premium calculation step"
                )
            
            # Extract and return agent-optimized results
            return self._create_agent_success_response(calculated_data, params)
            
        except Exception as e:
            logger.error(f"Rate tool execution failed: {str(e)}", exc_info=True)
            return self._create_agent_error_response(
                str(e),
                context="Unexpected error during processing"
            )
        finally:
            self._cleanup()
    
    def _apply_defaults(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values to parameters."""
        result = params.copy()
        
        # Apply defaults for missing optional fields
        for key, default_value in self.DEFAULT_VALUES.items():
            if key not in result or result[key] is None:
                result[key] = default_value
        
        return result
    
    def _create_policy(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Create a policy with the InsureMO API."""
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
        """Calculate premium for a created policy."""
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
        """Build the complete policy payload with defaults."""
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
    
    def _create_agent_success_response(self, calculated_data: Dict[str, Any], input_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create agent-optimized success response with summary.
        
        Args:
            calculated_data: Calculated policy data from API
            input_params: Original input parameters for context
            
        Returns:
            Agent-friendly response with summary
        """
        premium_breakdown = self._extract_premium_breakdown(calculated_data)
        
        # Format currency values
        def format_currency(amount):
            return f"${amount:,.2f}" if amount else "$0.00"
        
        # Create human-readable summary for agent
        summary_parts = [
            f"Successfully rated commercial insurance for {input_params.get('customerName')}.",
            f"Proposal #{calculated_data.get('ProposalNo')} created.",
            f"Total Annual Premium: {format_currency(calculated_data.get('TotalPremium', 0))}",
            f"Coverage Period: {calculated_data.get('EffectiveDate', 'Today')} to {calculated_data.get('ExpiryDate', 'One year')}",
        ]
        
        if premium_breakdown['glPremium'] > 0:
            summary_parts.append(f"General Liability: {format_currency(premium_breakdown['glPremium'])}")
        if premium_breakdown['propertyPremium'] > 0:
            summary_parts.append(f"Property Coverage: {format_currency(premium_breakdown['propertyPremium'])}")
        
        summary = " ".join(summary_parts)
        
        return {
            "success": True,
            "summary": summary,
            "proposalNo": calculated_data.get("ProposalNo"),
            "policyId": calculated_data.get("PolicyId"),
            "premiums": {
                "total": calculated_data.get("TotalPremium", 0),
                "gross": calculated_data.get("GrossPremium", 0),
                "generalLiability": premium_breakdown["glPremium"],
                "property": premium_breakdown["propertyPremium"],
                "commission": calculated_data.get("Commission", 0),
                "commissionRate": calculated_data.get("CommissionRate", 0)
            },
            "coverage": {
                "effectiveDate": calculated_data.get("EffectiveDate"),
                "expiryDate": calculated_data.get("ExpiryDate"),
                "term": "Annual"
            },
            "error": None,
            "agentInstructions": "Use the 'summary' field for customer communication. The 'premiums' object contains detailed breakdown for quote presentation."
        }
    
    def _create_agent_error_response(self, error_message: str, context: Any = None) -> Dict[str, Any]:
        """
        Create agent-friendly error response.
        
        Args:
            error_message: Error message
            context: Additional context for debugging
            
        Returns:
            Agent-friendly error response
        """
        logger.error(f"Error: {error_message}, Context: {context}")
        
        # Create agent-friendly error summary
        agent_summary = "Unable to generate insurance quote. "
        
        if "Missing required fields" in error_message:
            agent_summary += f"The following information is needed: {context if isinstance(context, list) else error_message}"
        elif "Failed to create policy" in error_message:
            agent_summary += "The insurance system couldn't process this business information. Please verify all details are correct."
        elif "Failed to calculate premium" in error_message:
            agent_summary += "The premium calculation couldn't be completed. The business may require manual underwriting."
        else:
            agent_summary += f"Technical issue: {error_message}"
        
        return {
            "success": False,
            "summary": agent_summary,
            "proposalNo": None,
            "policyId": None,
            "premiums": None,
            "coverage": None,
            "error": error_message,
            "agentInstructions": "Inform the customer about the issue and offer to collect any missing information or try alternative options."
        }


# PLATFORM INTEGRATION FUNCTION
def execute_tool(**kwargs) -> Dict[str, Any]:
    """
    Execute the InsureMO Rate Tool for platform integration.
    
    This is the standard entry point for the Blueprint framework and AI Agents.
    
    Args:
        **kwargs: Tool input parameters (can be raw JSON from agent)
        
    Returns:
        Dict containing rating results optimized for agent consumption
    """
    with InsuremoRateTool() as tool:
        return tool.run_sync(**kwargs)


# TESTING AND METADATA
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
    print(" InsureMO Rate Tool - Agent-Optimized Version")
    print("="*80)
    print(f" Version: {InsuremoRateTool.version}")
    print(f" Framework: Blueprint-Compliant with AI Agent Optimization")
    print("-"*80)
    
    print("\n📋 Tool Metadata:")
    print(json.dumps(tool_metadata, indent=2))
    
    print("\n✅ Agent Integration Features:")
    print("  1. ✓ Accepts JSON input from AI Agents")
    print("  2. ✓ Parses and sanitizes agent input")
    print("  3. ✓ Sends appropriate parameters to InsureMO API")
    print("  4. ✓ Returns agent-friendly JSON with summary")
    
    print("\n🚀 Key Improvements:")
    print("  - Added parse_agent_input() method for robust JSON handling")
    print("  - Enhanced error messages for agent understanding")
    print("  - Added 'summary' field for easy agent summarization")
    print("  - Included 'agentInstructions' for guidance")
    print("  - Streamlined response structure for agent consumption")
    
    print("\n📝 Example Agent Input:")
    example_input = {
        "customerName": "ABC Bakery LLC",
        "address1": "123 Main Street",
        "city": "Austin",
        "state": "TX",
        "zipCode": "78701",
        "businessType": "Retail",
        "fullTimeEmpl": 10,
        "buildingLimit": 750000
    }
    print(json.dumps(example_input, indent=2))
    
    print("\n📤 Example Agent Response Structure:")
    example_response = {
        "success": True,
        "summary": "Successfully rated commercial insurance for ABC Bakery LLC. Proposal #P2024-001 created. Total Annual Premium: $5,234.00",
        "proposalNo": "P2024-001",
        "premiums": {
            "total": 5234.00,
            "generalLiability": 2500.00,
            "property": 2734.00
        },
        "coverage": {
            "effectiveDate": "2024-01-15",
            "expiryDate": "2025-01-15",
            "term": "Annual"
        }
    }
    print(json.dumps(example_response, indent=2))
    
    print("\n" + "="*80)
    print(" Tool ready for AI Agent integration!")
    print("="*80)
