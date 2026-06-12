from ui.knowledge import (
    ComponentType,
    UIComponent,
    UIComponentKnowledge,
    UIService,
    get_ui_knowledge_registry,
)


def _create_azure_knowledge() -> UIComponentKnowledge:
    knowledge = UIComponentKnowledge(
        domain_id="azure",
        display_name="Azure Static Web Apps / Fluent UI",
        supported_element_types=[
            "button",
            "input",
            "select",
            "table",
            "form",
            "card",
            "navigation",
            "header",
            "footer",
            "tab",
            "chart",
            "filter",
            "checkbox",
            "radio",
            "text",
            "image",
            "icon",
            "dialog",
        ],
    )

    components = [
        UIComponent(
            component_id="comp-azure-fluent-button",
            name="FluentButton",
            library="@fluentui/react-components",
            component_type=ComponentType.CONTROL,
            supported_element_types=["button"],
            properties=["appearance", "icon", "shape", "size", "disabled"],
            events=["onClick"],
            documentation_url="https://learn.microsoft.com/en-us/fluent-ui/react components/button/",
            complexity=1,
            metadata={"deprecated": False, "responsive": True},
        ),
        UIComponent(
            component_id="comp-azure-fluent-input",
            name="FluentInput",
            library="@fluentui/react-components",
            component_type=ComponentType.CONTROL,
            supported_element_types=["input", "text"],
            properties=["placeholder", "type", "required", "errorMessage"],
            events=["onChange", "onBlur", "onFocus"],
            documentation_url="https://learn.microsoft.com/en-us/fluent-ui/react-components/input/",
            complexity=1,
            metadata={"deprecated": False, "responsive": True},
        ),
        UIComponent(
            component_id="comp-azure-fluent-select",
            name="FluentSelect",
            library="@fluentui/react-components",
            component_type=ComponentType.CONTROL,
            supported_element_types=["select", "dropdown"],
            properties=["placeholder", "multiSelect", "disabled"],
            events=["onChange", "onOptionSelect"],
            documentation_url="https://learn.microsoft.com/en-us/fluent-ui/react-components/combobox/",
            complexity=1,
            metadata={"deprecated": False, "responsive": True},
        ),
        UIComponent(
            component_id="comp-azure-fluent-table",
            name="FluentDataGrid",
            library="@fluentui/react-components",
            component_type=ComponentType.CONTROL,
            supported_element_types=["table"],
            properties=["items", "columns", "sortable", "resizable", "selectionMode"],
            events=["onSort", "onColumnResize", "onRowClick"],
            documentation_url="https://learn.microsoft.com/en-us/fluent-ui/react-components/data-grid/",
            complexity=2,
            metadata={"deprecated": False, "responsive": True},
        ),
        UIComponent(
            component_id="comp-azure-fluent-card",
            name="FluentCard",
            library="@fluentui/react-components",
            component_type=ComponentType.CONTROL,
            supported_element_types=["card"],
            properties=["width", "height", "orientation", "appearance"],
            events=[],
            documentation_url="https://learn.microsoft.com/en-us/fluent-ui/react-components/card/",
            complexity=1,
            metadata={"deprecated": False, "responsive": True},
        ),
        UIComponent(
            component_id="comp-azure-fluent-nav",
            name="FluentNav",
            library="@fluentui/react-components",
            component_type=ComponentType.CONTROL,
            supported_element_types=["navigation", "sidebar"],
            properties=["groups", "selectedValue", "expandedState"],
            events=["onNavigate", "onExpand"],
            documentation_url="https://learn.microsoft.com/en-us/fluent-ui/react-components/nav/",
            complexity=2,
            metadata={"deprecated": False, "responsive": True},
        ),
        UIComponent(
            component_id="comp-azure-fluent-dialog",
            name="FluentDialog",
            library="@fluentui/react-components",
            component_type=ComponentType.CONTROL,
            supported_element_types=["dialog", "modal"],
            properties=["open", "modalProps", "forceFocusInsideTrap"],
            events=["onDismiss", "onConfirm"],
            documentation_url="https://learn.microsoft.com/en-us/fluent-ui/react-components/dialog/",
            complexity=2,
            metadata={"deprecated": False, "responsive": True},
        ),
        UIComponent(
            component_id="comp-azure-fluent-tabs",
            name="FluentTabs",
            library="@fluentui/react-components",
            component_type=ComponentType.CONTROL,
            supported_element_types=["tab"],
            properties=["selectedValue", "size", "headersOnly"],
            events=["onTabSelect"],
            documentation_url="https://learn.microsoft.com/en-us/fluent-ui/react-components/tabs/",
            complexity=1,
            metadata={"deprecated": False, "responsive": True},
        ),
        UIComponent(
            component_id="comp-azure-fluent-checkbox",
            name="FluentCheckbox",
            library="@fluentui/react-components",
            component_type=ComponentType.CONTROL,
            supported_element_types=["checkbox"],
            properties=["label", "checked", "indeterminate", "disabled"],
            events=["onChange"],
            documentation_url="https://learn.microsoft.com/en-us/fluent-ui/react-components/checkbox/",
            complexity=1,
            metadata={"deprecated": False, "responsive": True},
        ),
    ]
    for comp in components:
        knowledge.components[comp.name] = comp

    services = [
        UIService(
            service_id="svc-azure-swa",
            name="Static Web Apps",
            service_type="hosting",
            capabilities=[
                "custom-domain",
                "authentication",
                "API-functions",
                "global-distribution",
            ],
            documentation_url="https://learn.microsoft.com/en-us/azure/static-web-apps/",
        ),
        UIService(
            service_id="svc-azure-ad",
            name="Microsoft Entra ID",
            service_type="authentication",
            capabilities=["OIDC", "MFA", "conditional-access", "B2C"],
            documentation_url="https://learn.microsoft.com/en-us/azure/active-directory/",
        ),
        UIService(
            service_id="svc-azure-cosmos",
            name="Cosmos DB",
            service_type="database",
            capabilities=["NoSQL", "MongoDB-API", "Gremlin", "Table-API", "global-distribution"],
            documentation_url="https://learn.microsoft.com/en-us/azure/cosmos-db/",
        ),
    ]
    for svc in services:
        knowledge.services[svc.name] = svc

    return knowledge


def _register_azure_knowledge():
    reg = get_ui_knowledge_registry()
    reg.register(_create_azure_knowledge())


_register_azure_knowledge()
