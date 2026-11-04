USER_FIELD_CONFIG = {
  "student_id": {
    "editable": False,
    "storage": "users",
    "type": "str"
  },
  "name": {
    "editable": True,
    "storage": "users",
    "type": "str",
    "label": "Name",
    "question": "What is your name?"
  },
  "birthday": {
    "editable": True,
    "storage": "users",
    "type": "str"
  },
  "gender": {
    "editable": True,
    "storage": "users",
    "type": "str"
  },
  "year": {
    "editable": True,
    "storage": "users",
    "type": "int"
  },
  "course": {
    "editable": True,
    "storage": "users",
    "type": "str"
  },
  "bio": {
    "editable": True,
    "storage": "users",
    "type": "str"
  },
  "religion": {
    "editable": True,
    "storage": "users",
    "type": "str"
  },
  "mbti": {
    "editable": True,
    "storage": "users",
    "type": "str"
  },
  "match_preference": {
    "editable": True,
    "storage": "users",
    "type": "str"
  },
  "here_for": {
    "editable": True,
    "storage": "users",
    "type": "str"
  },
  "expectations": {
    "editable": True,
    "storage": "users",
    "type": "str"
  },
  "ccas": {
    "editable": True,
    "storage": "ccas",
    "type": "list",
    "column_name": "cca"
  },
  "events": {
    "editable": True,
    "storage": "events",
    "type": "list",
    "column_name": "event"
  },
  "hobbies": {
    "editable": True,
    "storage": "hobbies",
    "type": "list",
    "column_name": "hobby"
  },
  "interests": {
    "editable": True,
    "storage": "interests",
    "type": "list",
    "column_name": "interest"
  },
  "tele_handle": {
    "editable": True,
    "storage": "users",
    "type": "str"
  },
} # TODO: Clint to add schema onto this config file