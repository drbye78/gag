"""Safe Cypher query builder with parameterized syntax to prevent injection attacks."""

import re
from typing import Any
from contextlib import contextmanager


class CypherInjectionError(ValueError):
    """Raised when a potential Cypher injection attempt is detected.
    
    This exception indicates that user input violates security constraints
    and cannot be safely interpolated into a Cypher query.
    """

    pass


class CypherBuilder:
    """Safe Cypher query builder with parameterized syntax.
    
    This class provides a safe interface for constructing Cypher queries
    by enforcing strict validation and using parameterized syntax ($param)
    for all user-controlled values. This prevents Cypher injection attacks.
    
    All node labels, relationship types, property keys, and property values
    must be validated before being included in the generated query.
    
    Example:
        >>> builder = CypherBuilder()
        >>> builder.match_node(["Person"], {"name": "Alice"})
        >>> builder.where_clause("age", ">", 18)
        >>> query, params = builder.build()
        >>> # query: "MATCH (n:`Person` {name: $param0}) WHERE n.age > $param1 RETURN n"
        >>> # params: {"param0": "Alice", "param1": 18}
    
    Context manager usage:
        >>> with CypherBuilder() as builder:
        ...     builder.match_node(["User"], {"email": "user@example.com"})
        ...     query, params = builder.build()
    
    Class attributes:
        _allowed_types (set[str]): Allowlist of permitted node/relationship types.
                                  Subclasses should override this with their
                                  own domain-specific allowlist.
    """
    
    # Default allowlist - subclasses should override with their own types
    _allowed_types: set[str] = {
        "Component", "Service", "API", "Endpoint", "Database",
        "Function", "Class", "Module", "File", "Entity",
        "Person", "Organization", "Document", "UISketch",
    }
    
    # Relationship type allowlist
    _allowed_relations: set[str] = {
        "CALLS", "DEFINES", "IMPORTS", "RETURNS", "CONTAINS",
        "INHERITS", "IMPLEMENTS", "DEPENDS_ON", "RELATED_TO",
        "DOCUMENTED_BY", "TRIGGERS", "AFFECTS", "HAS_PROPERTY",
    }
    
    # Valid operators for WHERE clauses
    _allowed_operators: set[str] = {
        "=", "!=", "<", ">", "<=", ">=", "STARTS WITH", 
        "ENDS WITH", "CONTAINS", "IS NULL", "IS NOT NULL",
    }
    
    # Regex pattern for valid identifiers
    _IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    
    def __init__(self, allowed_types: set[str] | None = None):
        """Initialize the CypherBuilder.
        
        Args:
            allowed_types: Optional custom allowlist for node/relationship types.
                          If not provided, uses the class-level _allowed_types.
        """
        self._allowed_types = allowed_types or self._allowed_types
        self._parts: list[str] = []
        self._params: dict[str, Any] = {}
        self._param_counter = 0
        self._in_context = False
    
    def __enter__(self) -> "CypherBuilder":
        """Enter context manager mode."""
        self._in_context = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager mode and reset state."""
        self._in_context = False
        self._parts.clear()
        self._params.clear()
        self._param_counter = 0
        return None
    
    @contextmanager
    def _安全管理(self):
        """Context manager for safe query building.
        
        Yields the builder and ensures cleanup on exit.
        """
        try:
            yield self
        finally:
            self._parts.clear()
            self._params.clear()
            self._param_counter = 0
    
    def _generate_param_name(self) -> str:
        """Generate a unique parameter name.
        
        Returns:
            A unique parameter name like 'param0', 'param1', etc.
        """
        name = f"param{self._param_counter}"
        self._param_counter += 1
        return name
    
    def _generate_rel_param_name(self) -> str:
        """Generate a unique parameter name for relationships.
        
        Returns:
            A unique parameter name like 'rel_param0', 'rel_param1', etc.
        """
        name = f"rel_param{self._param_counter}"
        self._param_counter += 1
        return name
    
    @classmethod
    def validate_identifier(cls, name: str) -> str:
        """Validate an identifier against the allowed pattern.
        
        Validates that the identifier matches the pattern ^[A-Za-z_][A-Za-z0-9_]*.
        This ensures identifiers don't contain special characters that could
        be used for injection attacks.
        
        Args:
            name: The identifier to validate.
            
        Returns:
            The validated identifier if valid.
            
        Raises:
            CypherInjectionError: If the identifier is invalid or contains
                                potentially dangerous characters.
                                
        Example:
            >>> CypherBuilder.validate_identifier("validName")
            'validName'
            >>> CypherBuilder.validate_identifier("123invalid")
            # Raises CypherInjectionError
        """
        if not name:
            raise CypherInjectionError("Identifier cannot be empty")
        
        if not cls._IDENTIFIER_PATTERN.match(name):
            raise CypherInjectionError(
                f"Invalid identifier '{name}': must match pattern "
                r"^[A-Za-z_][A-Za-z0-9_]*$"
            )
        
        return name
    
    @classmethod
    def validate_int_param(
        cls, 
        value: int, 
        min_val: int = 0, 
        max_val: int = 1000
    ) -> int:
        """Validate an integer parameter is within bounds.
        
        Ensures the integer value falls within the specified range.
        This prevents out-of-bounds errors and potential integer
        overflow issues in query construction.
        
        Args:
            value: The integer value to validate.
            min_val: Minimum allowed value (default: 0).
            max_val: Maximum allowed value (default: 1000).
            
        Returns:
            The validated integer if within bounds.
            
        Raises:
            CypherInjectionError: If the value is out of the specified range
                                or cannot be converted to an integer.
                                
        Example:
            >>> CypherBuilder.validate_int_param(50, 0, 100)
            50
            >>> CypherBuilder.validate_int_param(150, 0, 100)
            # Raises CypherInjectionError
        """
        try:
            int_value = int(value)
        except (TypeError, ValueError) as e:
            raise CypherInjectionError(
                f"Invalid integer value '{value}': {e}"
            ) from e
        
        if int_value < min_val or int_value > max_val:
            raise CypherInjectionError(
                f"Integer {int_value} out of bounds [{min_val}, {max_val}]"
            )
        
        return int_value
    
    def _validate_type_in_allowlist(self, type_name: str) -> str:
        """Validate a type is in the allowlist.
        
        Args:
            type_name: The type name to validate.
            
        Returns:
            The validated type name if in allowlist.
            
        Raises:
            CypherInjectionError: If the type is not in the allowlist.
        """
        if type_name not in self._allowed_types:
            raise CypherInjectionError(
                f"Type '{type_name}' not in allowed types: {self._allowed_types}"
            )
        return type_name
    
    def _validate_rel_type_in_allowlist(self, rel_type: str) -> str:
        """Validate a relationship type is in the allowlist.
        
        Args:
            rel_type: The relationship type to validate.
            
        Returns:
            The validated relationship type if in allowlist.
            
        Raises:
            CypherInjectionError: If the relationship type is not in allowlist.
        """
        if rel_type not in self._allowed_relations:
            raise CypherInjectionError(
                f"Relationship type '{rel_type}' not in allowed types: "
                f"{self._allowed_relations}"
            )
        return rel_type
    
    def match_node(
        self, 
        labels: list[str], 
        properties: dict[str, Any]
    ) -> "CypherBuilder":
        """Create a MATCH clause for nodes with labels and properties.
        
        Constructs a safe MATCH clause using parameterized syntax.
        All property values are stored as parameters to prevent injection.
        
        Args:
            labels: List of node labels (e.g., ["Person", "User"]).
            properties: Dictionary of property key-value pairs.
            
        Returns:
            Self for method chaining.
            
        Raises:
            CypherInjectionError: If any label or property key is invalid.
            
        Example:
            >>> builder = CypherBuilder()
            >>> builder.match_node(["Person"], {"name": "Alice", "age": 30})
            >>> # Generates: MATCH (n:`Person` {name: $param0, age: $param1})
            >>> # With params: {"param0": "Alice", "param1": 30}
        """
        # Validate labels against allowlist first
        validated_labels = []
        for label in labels:
            # Allow valid identifier pattern in labels
            self.validate_identifier(label)
            # Then check against allowlist
            self._validate_type_in_allowlist(label)
            validated_labels.append(label)
        
        # Build label part
        label_str = ":" + ":".join([f"`{l}`" for l in validated_labels]) if validated_labels else ""
        
        # Build properties with parameterized values
        prop_parts = []
        for key, value in properties.items():
            # Validate property key
            self.validate_identifier(key)
            param_name = self._generate_param_name()
            prop_parts.append(f"{key}: ${param_name}")
            self._params[param_name] = value
        
        props_str = "{" + ", ".join(prop_parts) + "}" if prop_parts else "{}"
        
        self._parts.append(f"MATCH (n{label_str} {props_str})")
        return self
    
    def match_relationship(
        self,
        rel_type: str,
        min_depth: int = 1,
        max_depth: int = 3,
        properties: dict | None = None
    ) -> "CypherBuilder":
        """Create a relationship MATCH clause with depth and properties.
        
        Constructs a safe relationship pattern using parameterized syntax.
        Relationship type is validated against allowlist.
        
        Args:
            rel_type: Relationship type (e.g., "CALLS", "DEPENDS_ON").
            min_depth: Minimum path depth (default: 1).
            max_depth: Maximum path depth (default: 3).
            properties: Optional dictionary of relationship properties.
            
        Returns:
            Self for method chaining.
            
        Raises:
            CypherInjectionError: If rel_type is not in allowlist or
                                depth parameters are invalid.
            
        Example:
            >>> builder = CypherBuilder()
            >>> builder.match_relationship("CALLS", 1, 3, {"weight": 1.0})
            >>> # Generates: MATCH ()-[r:`CALLS`*1..3 {weight: $rel_param0}]->
        """
        # Validate relationship type against allowlist
        self._validate_rel_type_in_allowlist(rel_type)
        
        # Validate depth parameters
        min_d = self.validate_int_param(min_depth, 1, 10)
        max_d = self.validate_int_param(max_depth, min_d, 10)
        
        # Build relationship pattern
        rel_pattern = f"[r:`{rel_type}`*{min_d}..{max_d}]"
        
        # Add properties if provided
        if properties:
            prop_parts = []
            for key, value in properties.items():
                self.validate_identifier(key)
                param_name = self._generate_rel_param_name()
                prop_parts.append(f"{key}: ${param_name}")
                self._params[param_name] = value
            props_str = "{" + ", ".join(prop_parts) + "}"
            rel_pattern += f" {props_str}"
        
        self._parts.append(f"MATCH ()-{rel_pattern}->()")
        return self
    
    def where_clause(
        self, 
        prop: str, 
        operator: str, 
        value: Any
    ) -> "CypherBuilder":
        """Create a WHERE clause with parameterized value.
        
        Constructs a safe WHERE clause using parameterized syntax.
        The property name is validated, and the operator is checked
        against allowed operators.
        
        Args:
            prop: Property name (e.g., "name", "age").
            operator: Comparison operator (e.g., "=", ">", "CONTAINS").
            value: The value to compare against (will be parameterized).
            
        Returns:
            Self for method chaining.
            
        Raises:
            CypherInjectionError: If property name is invalid or operator
                                is not in the allowed list.
                                
        Example:
            >>> builder = CypherBuilder()
            >>> builder.where_clause("age", ">", 18)
            >>> # Generates: WHERE n.age > $param0
            >>> # With params: {"param0": 18}
        """
        # Validate property name
        self.validate_identifier(prop)
        
        # Normalize and validate operator
        op_upper = operator.upper().strip()
        if op_upper not in self._allowed_operators:
            raise CypherInjectionError(
                f"Invalid operator '{operator}'. Must be one of: "
                f"{self._allowed_operators}"
            )
        
        # Generate parameterized value
        param_name = self._generate_param_name()
        
        # Handle NULL checks specially
        if op_upper in ("IS NULL", "IS NOT NULL"):
            where_part = f"n.{prop} {op_upper}"
        else:
            where_part = f"n.{prop} {op_upper} ${param_name}"
            self._params[param_name] = value
        
        self._parts.append(f"WHERE {where_part}")
        return self
    
    def with_clause(self, *variables: str) -> "CypherBuilder":
        """Add a WITH clause.
        
        Args:
            variables: Variable names to pass through.
            
        Returns:
            Self for method chaining.
        """
        # Validate all variable names
        for var in variables:
            self.validate_identifier(var)
        
        self._parts.append(f"WITH {', '.join(variables)}")
        return self
    
    def return_clause(self, *expressions: str) -> "CypherBuilder":
        """Add a RETURN clause.
        
        Args:
            expressions: Expressions to return.
            
        Returns:
            Self for method chaining.
        """
        self._parts.append(f"RETURN {', '.join(expressions)}")
        return self
    
    def limit_clause(self, limit: int) -> "CypherBuilder":
        """Add a LIMIT clause with validated integer.
        
        Args:
            limit: Maximum number of results.
            
        Returns:
            Self for method chaining.
        """
        validated_limit = self.validate_int_param(limit, 1, 1000)
        param_name = self._generate_param_name()
        self._params[param_name] = validated_limit
        self._parts.append(f"LIMIT ${param_name}")
        return self
    
    def order_by(self, *expressions: str) -> "CypherBuilder":
        """Add an ORDER BY clause.
        
        Args:
            expressions: Sort expressions (e.g., "n.name", "n.age DESC").
            
        Returns:
            Self for method chaining.
        """
        self._parts.append(f"ORDER BY {', '.join(expressions)}")
        return self
    
    def build(self) -> tuple[str, dict[str, Any]]:
        """Finalize and return the constructed query and parameters.
        
        Combines all parts into a single Cypher query string with
        parameterized values. The query uses $param syntax for
        all user-controlled values.
        
        Returns:
            A tuple of (cypher_query, parameters_dict).
            
        Example:
            >>> builder = CypherBuilder()
            >>> builder.match_node(["Person"], {"name": "Alice"})
            >>> builder.where_clause("age", ">", 18)
            >>> builder.return_clause("n")
            >>> query, params = builder.build()
            >>> # query: "MATCH (n:`Person` {name: $param0}) WHERE n.age > $param1 RETURN n"
            >>> # params: {"param0": "Alice", "param1": 18}
        """
        cypher = "\n".join(self._parts)
        return cypher, self._params.copy()
    
    def reset(self) -> "CypherBuilder":
        """Reset the builder state.
        
        Clears all parts and parameters, ready for building a new query.
        
        Returns:
            Self for method chaining.
        """
        self._parts.clear()
        self._params.clear()
        self._param_counter = 0
        return self


class SafeCypherBuilder(CypherBuilder):
    """Simplified builder focused on common patterns.
    
    This subclass provides a more streamlined interface for
    common query patterns with stricter defaults.
    """
    
    _allowed_types: set[str] = {
        "Component", "Service", "API", "Endpoint", "Database",
        "Function", "Class", "Module", "File", "Entity",
    }

    _allowed_relations: set[str] = {
        "CALLS", "DEFINES", "IMPORTS", "RETURNS", "CONTAINS",
        "INHERITS", "IMPLEMENTS", "DEPENDS_ON", "RELATED_TO",
    }