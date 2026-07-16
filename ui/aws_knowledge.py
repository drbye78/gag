from ui.knowledge import (
    ComponentType,
    UIComponent,
    UIService,
    UIComponentKnowledge,
    get_ui_knowledge_registry,
)


def _create_aws_knowledge() -> UIComponentKnowledge:
    knowledge = UIComponentKnowledge(
        domain_id="aws",
        display_name="AWS Amplify/Cognito",
        supported_element_types=[
            "button", "input", "select", "table", "form", "card",
            "navigation", "header", "footer", "tab", "chart", "filter",
            "checkbox", "radio", "text", "image",
        ],
    )

    components = [
        UIComponent(
            component_id="comp-aws-amplify-button",
            name="AmplifyButton",
            library="@aws-amplify/ui-react",
            component_type=ComponentType.CONTROL,
            supported_element_types=["button"],
            properties=["variant", "size", "isDisabled", "loadingText"],
            events=["onClick", "onMouseEnter"],
            documentation_url="https://ui.docs.aws.amazon.com/amplify/latest/react/ui-reference-components#button",
            complexity=1,
            metadata={"deprecated": False, "responsive": True},
        ),
        UIComponent(
            component_id="comp-aws-amplify-input",
            name="AmplifyInput",
            library="@aws-amplify/ui-react",
            component_type=ComponentType.CONTROL,
            supported_element_types=["input", "text"],
            properties=["label", "placeholder", "type", "isRequired", "hasError"],
            events=["onInput", "onChange", "onBlur"],
            documentation_url="https://ui.docs.aws.amazon.com/amplify/latest/react/ui-reference-components#text-field",
            complexity=1,
            metadata={"deprecated": False, "responsive": True},
        ),
        UIComponent(
            component_id="comp-aws-amplify-select",
            name="AmplifySelect",
            library="@aws-amplify/ui-react",
            component_type=ComponentType.CONTROL,
            supported_element_types=["select", "dropdown"],
            properties=["label", "options", "placeholder", "isDisabled"],
            events=["onChange", "onSelect"],
            documentation_url="https://ui.docs.aws.amazon.com/amplify/latest/react/ui-reference-components#select",
            complexity=1,
            metadata={"deprecated": False, "responsive": True},
        ),
        UIComponent(
            component_id="comp-aws-amplify-table",
            name="AmplifyDataTable",
            library="@aws-amplify/ui-react-datatable",
            component_type=ComponentType.CONTROL,
            supported_element_types=["table"],
            properties=["data", "columns", "itemsPerPage", "enableSelection", "highlightOnHover"],
            events=["onSort", "onPagination", "onRowClick"],
            documentation_url="https://ui.docs.aws.amazon.com/amplify/latest/react/ui-reference-components#data-table",
            complexity=2,
            metadata={"deprecated": False, "responsive": True},
        ),
        UIComponent(
            component_id="comp-aws-amplify-card",
            name="AmplifyCard",
            library="@aws-amplify/ui-react",
            component_type=ComponentType.CONTROL,
            supported_element_types=["card"],
            properties=["variant", "heading", "coverImage", "overflowHidden"],
            events=[],
            documentation_url="https://ui.docs.aws.amazon.com/amplify/latest/react/ui-reference-components#card",
            complexity=1,
            metadata={"deprecated": False, "responsive": True},
        ),
        UIComponent(
            component_id="comp-aws-amplify-nav",
            name="AmplifyNav",
            library="@aws-amplify/ui-react",
            component_type=ComponentType.CONTROL,
            supported_element_types=["navigation", "sidebar"],
            properties=["links", "logo", "hideAuth", "authenticated"],
            events=["onNavigate", "onSignOut"],
            documentation_url="https://ui.docs.aws.amazon.com/amplify/latest/react/ui-reference-components#navbar",
            complexity=2,
            metadata={"deprecated": False, "responsive": True},
        ),
        UIComponent(
            component_id="comp-aws-amplify-form",
            name="AmplifyForm",
            library="@aws-amplify/ui-react",
            component_type=ComponentType.CONTROL,
            supported_element_types=["form"],
            properties=["id", "handleSubmit", "validationSchema"],
            events=["onSubmit", "onValidate", "onSuccess", "onError"],
            documentation_url="https://ui.docs.aws.amazon.com/amplify/latest/react/ui-reference-components#form",
            complexity=2,
            metadata={"deprecated": False, "responsive": True},
        ),
        UIComponent(
            component_id="comp-aws-amplify-checkbox",
            name="AmplifyCheckbox",
            library="@aws-amplify/ui-react",
            component_type=ComponentType.CONTROL,
            supported_element_types=["checkbox"],
            properties=["label", "name", "checked", "disabled"],
            events=["onChange", "onBlur"],
            documentation_url="https://ui.docs.aws.amazon.com/amplify/latest/react/ui-reference-components#checkbox",
            complexity=1,
            metadata={"deprecated": False, "responsive": True},
        ),
    ]
    for comp in components:
        knowledge.components[comp.name] = comp

    services = [
        UIService(
            service_id="svc-aws-cognito",
            name="Cognito",
            service_type="authentication",
            capabilities=["user-signup", "sign-in", "MFA", "social-sign-in", "lambda-trigger"],
            documentation_url="https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity.html",
        ),
        UIService(
            service_id="svc-aws-amplify-hosting",
            name="Amplify Hosting",
            service_type="hosting",
            capabilities=["git-workflow", "branch-deploy", "custom-domain", "redirect-rules"],
            documentation_url="https://docs.aws.amazon.com/amplify/latest/userguide/hosting.html",
        ),
        UIService(
            service_id="svc-aws-dynamodb",
            name="DynamoDB",
            service_type="database",
            capabilities=["NoSQL", "document-API", "DAX", "streams"],
            documentation_url="https://docs.aws.amazon.com/amazondynamodb/latest/devguide/",
        ),
    ]
    for svc in services:
        knowledge.services[svc.name] = svc

    return knowledge


def _register_aws_knowledge():
    reg = get_ui_knowledge_registry()
    reg.register(_create_aws_knowledge())


_register_aws_knowledge()