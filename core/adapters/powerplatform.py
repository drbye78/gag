from typing import Any, Dict, List, Optional
from core.adapters.base import AdapterInput, AdapterOutput, PlatformAdapter, AdapterRegistry, get_adapter_registry
from core.adapters.mixins import RecommendationMixin
from core.patterns.schema import Pattern, get_pattern_library
from core.constraints.engine import get_constraint_engine
from models.ir import IRFeature, PlatformContext


class PowerPlatformAdapter(RecommendationMixin, PlatformAdapter):
    @property
    def platform_id(self) -> str:
        return "powerplatform"
    
    @property
    def supported_services(self) -> List[str]:
        return [
            "powerapps",
            "powerpages",
            "powerautomate",
            "powerbi",
            "dataverse",
            "dynamics",
            "copilot-studio",
            "ai-builder",
            "connectors",
            "premium-connectors",
            "custom-connectors",
        ]
    
    @property
    def patterns(self) -> List[Pattern]:
        library = get_pattern_library()
        
        power_patterns = [
            Pattern(
                id="pp_powerapps_canvas",
                name="Power Apps Canvas",
                domain="architecture",
                triggers=["canvas", "powerapps-canvas"],
                conditions=[],
                components=["canvas-app", "dataverse"],
                benefits=["No-code", "Fast development", "Mobile"],
                tradeoffs=["Complexity limits", "Licensing"],
                priority=9,
                confidence=0.9,
            ),
            Pattern(
                id="pp_powerapps_model",
                name="Power Apps Model-Driven",
                domain="architecture",
                triggers=["model-driven", "dynamics"],
                conditions=[],
                components=["model-app", "dataverse"],
                benefits=["Enterprise features", "Complex forms"],
                tradeoffs=["Less flexibility"],
                priority=8,
                confidence=0.85,
            ),
            Pattern(
                id="pp_powerautomate",
                name="Power Automate Flow",
                domain="architecture",
                triggers=["flow", "powerautomate"],
                conditions=[],
                components=["flow", "connector"],
                benefits=["Automation", "300+ connectors"],
                tradeoffs=["Execution limits", "Complexity"],
                priority=9,
                confidence=0.9,
            ),
            Pattern(
                id="pp_powerpages",
                name="Power Pages",
                domain="architecture",
                triggers=["powerpages", "portal"],
                conditions=[],
                components=["website", "dataverse"],
                benefits=["External facing", "Authentication"],
                tradeoffs=["Customization limits"],
                priority=8,
                confidence=0.8,
            ),
            Pattern(
                id="pp_copilot",
                name="Copilot Studio",
                domain="architecture",
                triggers=["copilot", "ai-builder"],
                conditions=[],
                components=["copilot", "knowledge-base"],
                benefits=["AI chatbot", "Native integration"],
                tradeoffs=["AI credits", "Training needed"],
                priority=8,
                confidence=0.75,
            ),
            Pattern(
                id="pp_dataverse",
                name="Dataverse",
                domain="data",
                triggers=["dataverse", "table"],
                conditions=[],
                components=["dataverse-table", "relationships"],
                benefits=["Relational", "Security", "Audit"],
                tradeoffs=["Storage costs"],
                priority=9,
                confidence=0.95,
            ),
        ]
        
        for p in power_patterns:
            library.register(p)
        
        return power_patterns
    
    @property
    def constraints(self) -> Any:
        return get_constraint_engine()._constraint_sets.get("powerplatform")
    
    def transform_ir_to_platform(self, input: AdapterInput) -> AdapterOutput:
        features = input.ir_features
        pattern_results = input.pattern_matches
        violations = input.constraint_violations
        
        config_templates = self.generate_config(features)
        code_snippets = self.generate_code(features)
        
        recommendations = self._build_recommendations(
            pattern_results,
            features,
            violations
        )
        
        can_deploy = not any(
            v.severity == "error" for v in violations
        )
        
        confidence = sum(p.match_score for p in pattern_results) / max(1, len(pattern_results))
        
        return AdapterOutput(
            recommendations=recommendations,
            config_templates=config_templates,
            code_snippets=code_snippets,
            explanation=self._explain(recommendations, violations),
            confidence=confidence,
            can_deploy=can_deploy,
        )
    
    def generate_config(self, features: IRFeature) -> Dict[str, str]:
        configs = {}
        
        configs["dataverse-table.json"] = self._generate_dataverse_table(features)
        
        if features.has_api:
            configs["powerautomate-flow.json"] = self._generate_flow_config(features)
        
        if features.has_ui:
            configs["canvas-app-manifest.json"] = self._generate_canvas_manifest(features)
        
        return configs
    
    def generate_code(self, features: IRFeature) -> Dict[str, str]:
        code = {}
        
        code["powerapps-manifest.json"] = self._generate_manifest()
        
        if features.has_api:
            code["powerautomate-definition.json"] = self._generate_flow_definition()
        
        return code
    
    def _generate_dataverse_table(self, features: IRFeature) -> str:
        return '''{
  "@odata.type": "#Microsoft.Dynamics.CRM.Table",
  "Name": "MyCustomTable",
  "TableType": "Standard",
  "SchemaName": "cr4fc_MyCustomTable",
  "Columns": [
    {
      "Name": "Name",
      "LogicalName": "cr4fc_name",
      "Type": "String",
      "RequiredLevelLevel": {
        "Value": "ApplicationRequired"
      },
      "MaxLength": 100
    },
    {
      "Name": "Description",
      "LogicalName": "cr4fc_description",
      "Type": "String",
      "MaxLength": 500
    },
    {
      "Name": "Active",
      "LogicalName": "cr4fc_active",
      "Type": "Boolean",
      "DefaultValue": true
    }
  ],
  "PrimaryNameAttribute": "cr4fc_name",
  "PrimaryIdAttribute": "cr4fc_mycustomtableid"
}'''
    
    def _generate_flow_config(self, features: IRFeature) -> str:
        return '''{
  "properties": {
    "definition": {
      "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2017-03-01-preview/logicapps/flow.json",
      "actions": {
        "Send_an_email": {
          "inputs": {
            "body": {
              "Body": "@triggerBody()",
              "Subject": "Flow Notification"
            },
            "host": {
              "operationName": "SendEmailV2"
            }
          },
          "runAfter": {},
          "type": "Request"
        }
      },
      "triggers": {
        "manual": {
          "inputs": {},
          "kind": "Request",
          "type": "Request"
        }
      }
    },
    "state": "Enabled"
  }
}'''
    
    def _generate_canvas_manifest(self, features: IRFeature) -> str:
        return '''{
  "docSchemaVersion": "4.0",
  "docVersion": "1.0",
  "id": "my-canvas-app",
  "lastModifiedDateTime": "2024-01-01T00:00:00.000Z",
  "name": "MyCanvasApp",
  "publisherData": {
    "publisher": "myorg"
  },
  "resources": {
    "dataSources": {
      "Dataverse": {
        "dataset": "default",
        "table": "cr4fc_mycustomtable"
      }
    }
  },
  "screenLayouts": {
    "MainScreen": {
      "columns": [
        {
          "controlTemplateName": "text",
          "index": 0
        }
      ]
    }
  }
}'''
    
    def _generate_manifest(self) -> str:
        return '''{
  "schemaVersion": "1.0",
  "appDefinition": {
    "id": "my-powerapps-app",
    "name": "My Power Apps",
    "description": "Generated from Intelligence Platform",
    "publisher": "myorg",
    "version": "1.0.0",
    "appDefinitionTemplate": "canvas",
    "backgroundColor": "#0078D4",
    "iconUri": "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMDAgMTAwIiBmaWxsPSIjMDA3OGQ0Ii8+"
  },
  "screens": [
    {
      "name": "MainScreen",
      "components": []
    }
  ]
}'''
    
    def _generate_flow_definition(self) -> str:
        return '''{
  "properties": {
    "apiId": "/providers/Microsoft.Logic/usEastUS/workflows",
    "definition": {
      "$schema": "http://schema.json.org",
      "contentVersion": "1.0.0.0",
      "actions": {
        "Respond": {
          "inputs": {
            "statusCode": 200,
            "body": {
              "result": "@triggerBody()"
            }
          },
          "runAfter": {},
          "type": "Response"
        }
      },
      "trigger": {
        "type": "Request",
        "kind": "Http",
        "inputs": {
          "schema": {
            "type": "object",
            "properties": {}
          }
        }
      }
    }
  },
  "location": "eastus",
  "state": "Enabled"
}'''
        return

def register_powerplatform_adapter(registry=None):
    if registry:
        registry.register(PowerPlatformAdapter())