Feature: simple feature

  Scenario Outline: simple scenario outline
    Given exemplar <example_value> given
    When exemplar <example_value> when
    Then exemplar <example_value> then

    Examples: example
      | example_value |
      | value A       |