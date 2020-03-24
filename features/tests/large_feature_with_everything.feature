Feature: Large feature with everything

  Scenario Outline: Passed scenario outline with more tables and examples <example_value>
    Given exemplar <example_value> given
    And exemplar <example_value> given
    """
    plaintext docstring
    """
    When exemplar <example_value> when
    And exemplar <example_value> when
    """json
    {
      "key": "<example_value>",
      "info": "this docstring is automatically parsed as JSON because it is marked as 'json'"
    }
    """
    Then exemplar <example_value> then
      | name    |
      | value S |
      | files T |
    And exemplar <example_value> then
      | first_name | last_name | nickname    |
      | Big        | Lebowski  | El Duderino |
      | John       | Doe       | Unknown     |

    Examples: example
      | example_value |
      | files A       |
      | value B       |

  Scenario Outline: Mixed scenario outline with more tables and examples <example_value>
    Given empty given
    And exemplar <example_value> given
    """
    plaintext docstring
    """
    When exemplar <example_value> when
    """md
    markdown docstring
    """
    And exemplar <example_value> when
    """json
    {
      "key": "<example_value>",
      "info": "this docstring is automatically parsed as JSON because it is marked as 'json'"
    }
    """
    Then exemplar <example_value> then
      | name    |
      | files S |
      | value T |
    And exemplar <example_value> then
      | first_name | last_name | nickname    |
      | Big        | Lebowski  | El Duderino |
      | John       | Doe       | Unknown     |

    Examples: example
      | example_value |
      | files A       |
      | value B       |

    Examples: example
      | example_value |
      | files X       |
      | value Y       |

    @skipme
    Examples: skipped
      | example_value |
      | skipped U     |
      | skipped V     |

    @skipme
    Examples: skipped
      | example_value |
      | skipped O     |
      | skipped P     |

    Examples: example
      | example_value |
      | failure E     |
      | failure F     |

    Examples: example
      | example_value   |
      | failure files G |
      | failure H       |

  @skipme
  Scenario Outline: Skipped scenario outline <example_value>
    Given exemplar <example_value> given

    Examples: example
      | example_value |
      | value A       |

  Scenario Outline: Failed scenario outline <example_value>
    Given empty given
    When exemplar <example_value> when

    Examples: example
      | example_value   |
      | failure E       |
      | failure files F |

    Examples: example
      | example_value   |
      | failure G       |
      | failure files H |

  Scenario: simple scenario
    Given empty given
    When empty when
    Then empty then

  @skipme
  Scenario: skipped scenario
    Given empty given
    When empty when
    Then empty then

  Scenario: failed scenario
    Given empty given
    When exemplar failed when
    Then empty then