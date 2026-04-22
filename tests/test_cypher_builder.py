"""Tests for CypherBuilder - safe Cypher query construction."""

import pytest
from graph.cypher_builder import (
    CypherBuilder,
    SafeCypherBuilder,
    CypherInjectionError,
)


class TestValidateIdentifier:
    """Tests for validate_identifier method."""

    def test_valid_identifier(self):
        assert CypherBuilder.validate_identifier("validName") == "validName"
        assert CypherBuilder.validate_identifier("valid_name") == "valid_name"
        assert CypherBuilder.validate_identifier("name123") == "name123"
        assert CypherBuilder.validate_identifier("_private") == "_private"

    def test_valid_identifier_underscore(self):
        assert CypherBuilder.validate_identifier("_") == "_"
        assert CypherBuilder.validate_identifier("_foo") == "_foo"

    def test_invalid_identifier_starts_with_number(self):
        with pytest.raises(CypherInjectionError) as exc:
            CypherBuilder.validate_identifier("123invalid")
        assert "Invalid identifier" in str(exc.value)

    def test_invalid_identifier_special_chars(self):
        with pytest.raises(CypherInjectionError) as exc:
            CypherBuilder.validate_identifier("bad;name")
        assert "Invalid identifier" in str(exc.value)

    def test_invalid_identifier_dash(self):
        with pytest.raises(CypherInjectionError) as exc:
            CypherBuilder.validate_identifier("bad-name")
        assert "Invalid identifier" in str(exc.value)

    def test_invalid_identifier_dot(self):
        with pytest.raises(CypherInjectionError) as exc:
            CypherBuilder.validate_identifier("bad.name")
        assert "Invalid identifier" in str(exc.value)

    def test_invalid_identifier_space(self):
        with pytest.raises(CypherInjectionError) as exc:
            CypherBuilder.validate_identifier("bad name")
        assert "Invalid identifier" in str(exc.value)

    def test_empty_identifier(self):
        with pytest.raises(CypherInjectionError) as exc:
            CypherBuilder.validate_identifier("")
        assert "cannot be empty" in str(exc.value)

    def test_injection_attempt_backtick(self):
        with pytest.raises(CypherInjectionError) as exc:
            CypherBuilder.validate_identifier("`")
        assert "Invalid identifier" in str(exc.value)

    def test_injection_attempt_quote(self):
        with pytest.raises(CypherInjectionError) as exc:
            CypherBuilder.validate_identifier("' OR '1'='1")
        assert "Invalid identifier" in str(exc.value)


class TestValidateIntParam:
    """Tests for validate_int_param method."""

    def test_valid_int(self):
        assert CypherBuilder.validate_int_param(50, 0, 100) == 50
        assert CypherBuilder.validate_int_param(0, 0, 100) == 0
        assert CypherBuilder.validate_int_param(100, 0, 100) == 100

    def test_valid_string_int(self):
        assert CypherBuilder.validate_int_param("50", 0, 100) == 50
        assert CypherBuilder.validate_int_param("0", 0, 100) == 0

    def test_out_of_bounds_min(self):
        with pytest.raises(CypherInjectionError) as exc:
            CypherBuilder.validate_int_param(-1, 0, 100)
        assert "out of bounds" in str(exc.value)

    def test_out_of_bounds_max(self):
        with pytest.raises(CypherInjectionError) as exc:
            CypherBuilder.validate_int_param(101, 0, 100)
        assert "out of bounds" in str(exc.value)

    def test_invalid_string(self):
        with pytest.raises(CypherInjectionError) as exc:
            CypherBuilder.validate_int_param("not_a_number", 0, 100)
        assert "Invalid integer" in str(exc.value)

    def test_none_value(self):
        with pytest.raises(CypherInjectionError) as exc:
            CypherBuilder.validate_int_param(None, 0, 100)
        assert "Invalid integer" in str(exc.value)

    def test_default_bounds(self):
        assert CypherBuilder.validate_int_param(500) == 500
        assert CypherBuilder.validate_int_param(0) == 0
        assert CypherBuilder.validate_int_param(1000) == 1000


class TestMatchNode:
    """Tests for match_node method."""

    def test_match_simple_node(self):
        builder = CypherBuilder()
        builder.match_node(["Person"], {"name": "Alice"})
        cypher, params = builder.build()
        assert "MATCH (n:`Person`" in cypher
        assert "name: $param" in cypher
        assert params["param0"] == "Alice"

    def test_match_node_multiple_labels(self):
        builder = CypherBuilder()
        builder.match_node(["Person", "Entity"], {"id": 123})
        cypher, params = builder.build()
        assert "Person" in cypher
        assert "Entity" in cypher

    def test_match_node_multiple_properties(self):
        builder = CypherBuilder()
        builder.match_node(
            ["Person"], {"name": "Alice", "age": 30, "active": True}
        )
        cypher, params = builder.build()
        assert "name: $param" in cypher
        assert "age: $param" in cypher
        assert "active: $param" in cypher
        assert params["param0"] == "Alice"
        assert params["param1"] == 30
        assert params["param2"] is True

    def test_invalid_label(self):
        builder = CypherBuilder()
        with pytest.raises(CypherInjectionError) as exc:
            builder.match_node(["InvalidType"], {"name": "test"})
        assert "not in allowed types" in str(exc.value)

    def test_invalid_property_key(self):
        builder = CypherBuilder()
        with pytest.raises(CypherInjectionError) as exc:
            builder.match_node(["Person"], {"bad;key": "value"})
        assert "Invalid identifier" in str(exc.value)

    def test_safe_node_with_valid_type(self):
        builder = CypherBuilder()
        builder.match_node(["Entity"], {"name": "test"})
        cypher, params = builder.build()
        assert "MATCH (n:`Entity`" in cypher
        assert params["param0"] == "test"


class TestMatchRelationship:
    """Tests for match_relationship method."""

    def test_match_simple_relationship(self):
        builder = CypherBuilder()
        builder.match_relationship("CALLS", 1, 2)
        cypher, params = builder.build()
        assert "CALLS" in cypher
        assert "*1..2" in cypher

    def test_match_relationship_with_properties(self):
        builder = CypherBuilder()
        builder.match_relationship("CALLS", 1, 3, {"weight": 1.0})
        cypher, params = builder.build()
        assert "weight: $rel_param" in cypher
        assert params["rel_param0"] == 1.0

    def test_invalid_relationship_type(self):
        builder = CypherBuilder()
        with pytest.raises(CypherInjectionError) as exc:
            builder.match_relationship("INVALID", 1, 3)
        assert "not in allowed types" in str(exc.value)

    def test_injection_in_relationship_type(self):
        builder = CypherBuilder()
        with pytest.raises(CypherInjectionError) as exc:
            builder.match_relationship("CALLS; MATCH (n) DETACH DELETE n", 1, 3)
        assert "not in allowed types" in str(exc.value)

    def test_depth_validation(self):
        builder = CypherBuilder()
        with pytest.raises(CypherInjectionError) as exc:
            builder.match_relationship("CALLS", 0, 3)
        assert "out of bounds" in str(exc.value)


class TestWhereClause:
    """Tests for where_clause method."""

    def test_where_equals(self):
        builder = CypherBuilder()
        builder.where_clause("name", "=", "Alice")
        cypher, params = builder.build()
        assert "WHERE n.name = $param" in cypher
        assert params["param0"] == "Alice"

    def test_where_greater_than(self):
        builder = CypherBuilder()
        builder.where_clause("age", ">", 18)
        cypher, params = builder.build()
        assert "WHERE n.age > $param" in cypher
        assert params["param0"] == 18

    def test_where_not_equals(self):
        builder = CypherBuilder()
        builder.where_clause("status", "!=", "deleted")
        cypher, params = builder.build()
        assert "WHERE n.status != $param" in cypher

    def test_where_contains(self):
        builder = CypherBuilder()
        builder.where_clause("name", "CONTAINS", "test")
        cypher, params = builder.build()
        assert "WHERE n.name CONTAINS $param" in cypher

    def test_where_starts_with(self):
        builder = CypherBuilder()
        builder.where_clause("email", "STARTS WITH", "admin")
        cypher, params = builder.build()
        assert "WHERE n.email STARTS WITH $param" in cypher

    def test_where_is_null(self):
        builder = CypherBuilder()
        builder.where_clause("deleted_at", "IS NULL", None)
        cypher, params = builder.build()
        assert "WHERE n.deleted_at IS NULL" in cypher

    def test_where_is_not_null(self):
        builder = CypherBuilder()
        builder.where_clause("email", "IS NOT NULL", None)
        cypher, params = builder.build()
        assert "WHERE n.email IS NOT NULL" in cypher

    def test_invalid_property(self):
        builder = CypherBuilder()
        with pytest.raises(CypherInjectionError) as exc:
            builder.where_clause("bad;prop", "=", "value")
        assert "Invalid identifier" in str(exc.value)

    def test_invalid_operator(self):
        builder = CypherBuilder()
        with pytest.raises(CypherInjectionError) as exc:
            builder.where_clause("name", "LIKE", "pattern")
        assert "Invalid operator" in str(exc.value)

    def test_injection_in_property(self):
        builder = CypherBuilder()
        with pytest.raises(CypherInjectionError) as exc:
            builder.where_clause("name; RETURN 1", "=", "value")
        assert "Invalid identifier" in str(exc.value)


class TestFullQueryConstruction:
    """Tests for complete query building."""

    def test_full_query(self):
        builder = CypherBuilder()
        builder.match_node(["Person"], {"name": "Alice"})
        builder.where_clause("age", ">", 18)
        builder.return_clause("n")
        cypher, params = builder.build()
        assert "MATCH" in cypher
        assert "WHERE" in cypher
        assert "RETURN" in cypher

    def test_param_substitution(self):
        builder = CypherBuilder()
        builder.match_node(["Person"], {"name": "Bob"})
        builder.where_clause("age", ">", 25)
        builder.return_clause("n")
        cypher, params = builder.build()
        assert "param0" in params
        assert "param1" in params
        assert params["param0"] == "Bob"
        assert params["param1"] == 25

    def test_order_by_and_limit(self):
        builder = CypherBuilder()
        builder.match_node(["Person"], {"active": True})
        builder.order_by("n.name")
        builder.limit_clause(10)
        cypher, params = builder.build()
        assert "ORDER BY" in cypher
        assert "LIMIT" in cypher

    def test_with_clause(self):
        builder = CypherBuilder()
        builder.match_node(["Person"], {})
        builder.with_clause("n")
        builder.return_clause("count(n)")
        cypher, params = builder.build()
        assert "WITH n" in cypher
        assert "RETURN count(n)" in cypher


class TestContextManager:
    """Tests for context manager functionality."""

    def test_context_manager(self):
        with CypherBuilder() as builder:
            builder.match_node(["Person"], {"name": "test"})
            cypher, params = builder.build()
        assert "MATCH" in cypher

    def test_context_manager_cleanup(self):
        with CypherBuilder() as builder:
            builder.match_node(["Person"], {"name": "test"})
        assert builder._parts == []
        assert builder._params == {}


class TestReset:
    """Tests for reset method."""

    def test_reset(self):
        builder = CypherBuilder()
        builder.match_node(["Person"], {"name": "test"})
        builder.reset()
        cypher, params = builder.build()
        assert cypher == ""
        assert params == {}


class TestInjectionPrevention:
    """Tests demonstrating injection prevention."""

    def test_prevent_entity_type_injection(self):
        builder = CypherBuilder()
        with pytest.raises(CypherInjectionError):
            builder.match_node(["Person'; RETURN 1"], {})

    def test_prevent_relationship_type_injection(self):
        builder = CypherBuilder()
        with pytest.raises(CypherInjectionError):
            builder.match_relationship("CALLS DETACH DELETE", 1, 3)

    def test_prevent_property_key_injection(self):
        builder = CypherBuilder()
        with pytest.raises(CypherInjectionError):
            builder.match_node(["Person"], {"name; RETURN 1": "value"})

    def test_prevent_where_property_injection(self):
        builder = CypherBuilder()
        with pytest.raises(CypherInjectionError):
            builder.where_clause("name RETURN 1", "=", "value")

    def test_parameterized_values_prevent_injection(self):
        builder = CypherBuilder()
        malicious_name = "Alice'; MATCH (n) DETACH DELETE n RETURN '"
        builder.match_node(["Person"], {"name": malicious_name})
        cypher, params = builder.build()
        assert params["param0"] == malicious_name
        assert "DETACH DELETE" not in cypher


class TestSafeCypherBuilder:
    """Tests for SafeCypherBuilder subclass."""

    def test_restricted_types(self):
        builder = SafeCypherBuilder()
        with pytest.raises(CypherInjectionError):
            builder.match_node(["Person"], {"name": "test"})

    def test_allowed_types(self):
        builder = SafeCypherBuilder()
        builder.match_node(["Entity"], {"name": "test"})
        cypher, params = builder.build()
        assert "MATCH" in cypher


class TestMethodChaining:
    """Tests for fluent interface."""

    def test_method_chaining(self):
        builder = CypherBuilder()
        result = (
            builder
            .match_node(["Person"], {"name": "test"})
            .where_clause("age", ">", 18)
            .return_clause("n")
            .limit_clause(10)
        )
        assert result is builder