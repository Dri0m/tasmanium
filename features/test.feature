@a
Feature: ficurka

  @b @c
  Scenario Outline: Fly in <device>
    Given A user that can fly in <device>
    """plaintext or whatever
    line 1
    line 2
    """
    When WHEE
      | name   | email              | twitter         |
      | Aslak  | aslak@cucumber.io  | @aslak_hellesoy |

      | Julien | julien@cucumber.io | @jbpros         |
      | Matt   | matt@cucumber.io   | @mattwynne      |
    Then OOF

    @example_tag
    Examples: Sci-Fi
      | device  | unused thingy |
      | Jetpack | hehe          |
      | Ufo     | haha          |

    Examples: Totally normal
      | device | another unused thingy |
      | Glider | hehe                  |
      | Plane  | haha                  |

  Scenario: Walk
    Given A user that can walk on ground
    Then He walketh