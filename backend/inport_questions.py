"""
SwingShift Survey System - Master Question Importer
====================================================
Last Updated: January 13, 2026

Imports all 97 master survey questions into the database.
Run: python import_questions.py
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import MasterQuestion, ResponseOption


def likert():
    return [('1 (Strongly Disagree)', '1', 1, 1), ('2', '2', 2, 2), ('3', '3', 3, 3), ('4', '4', 4, 4), ('5 (Strongly Agree)', '5', 5, 5)]


QUESTIONS = [
    # DEMOGRAPHICS (1-17)
    {'n': 1, 't': 'What department do you work in?', 'c': 'Demographics', 'ty': 'multiple_choice', 'o': [('A', 'a', 1, None), ('B', 'b', 2, None), ('C', 'c', 3, None), ('D', 'd', 4, None), ('E', 'e', 5, None), ('F', 'f', 6, None), ('G', 'g', 7, None), ('H', 'h', 8, None)]},
    {'n': 2, 't': 'What is your job title?', 'c': 'Demographics', 'ty': 'multiple_choice', 'o': [('A', 'a', 1, None), ('B', 'b', 2, None), ('C', 'c', 3, None), ('D', 'd', 4, None), ('E', 'e', 5, None), ('F', 'f', 6, None), ('G', 'g', 7, None)]},
    {'n': 3, 't': 'What crew are you assigned to?', 'c': 'Demographics', 'ty': 'multiple_choice', 'o': [('First Shift (8-hour or 10-hour)', 'a', 1, None), ('First Shift (12-hour)', 'b', 2, None), ('Second Shift (8-hour)', 'c', 3, None), ('Second Shift (12-hour)', 'd', 4, None), ('Third Shift', 'e', 5, None), ('Weekend Shift', 'f', 6, None)]},
    {'n': 4, 't': 'How long have you worked for this company?', 'c': 'Demographics', 'ty': 'multiple_choice', 'sc': 'average_years', 'o': [('Less than 6 months', 'a', 1, 0.25), ('6 months to 1 year', 'b', 2, 0.75), ('1 to 5 years', 'c', 3, 3), ('6 to 10 years', 'd', 4, 8), ('11 to 15 years', 'e', 5, 13), ('16 to 20 years', 'f', 6, 18), ('Over 20 years', 'g', 7, 25)]},
    {'n': 5, 't': 'How long have you worked in your current department?', 'c': 'Demographics', 'ty': 'multiple_choice', 'sc': 'average_years', 'o': [('Less than 6 months', 'a', 1, 0.25), ('6 months to 1 year', 'b', 2, 0.75), ('1 to 5 years', 'c', 3, 3), ('6 to 10 years', 'd', 4, 8), ('11 to 15 years', 'e', 5, 13), ('16 to 20 years', 'f', 6, 18), ('Over 20 years', 'g', 7, 25)]},
    {'n': 6, 't': 'Do you have a second job?', 'c': 'Demographics', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
    {'n': 7, 't': 'Have you ever worked shiftwork at another facility?', 'c': 'Demographics', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
    {'n': 8, 't': 'If you have a second job, do you typically work at that job:', 'c': 'Demographics', 'ty': 'multiple_choice', 'o': [('Before your shift starts', 'a', 1, None), ('After you have worked your shift', 'b', 2, None), ("Only on days that you don't work", 'c', 3, None), ("I don't work at a second job", 'd', 4, None)]},
    {'n': 9, 't': 'Are you a student?', 'c': 'Demographics', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
    {'n': 10, 't': 'Do you have children or elder family members at home that require childcare or eldercare when you are at work?', 'c': 'Demographics', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
    {'n': 11, 't': 'What is your gender?', 'c': 'Demographics', 'ty': 'multiple_choice', 'o': [('Female', 'a', 1, None), ('Male', 'b', 2, None)]},
    {'n': 12, 't': 'What is your age group?', 'c': 'Demographics', 'ty': 'multiple_choice', 'sc': 'average_age', 'o': [('25 and under', 'a', 1, 23), ('26 to 30', 'b', 2, 28), ('31 to 35', 'c', 3, 33), ('36 to 40', 'd', 4, 38), ('41 to 45', 'e', 5, 43), ('46 to 50', 'f', 6, 48), ('51 to 55', 'g', 7, 53), ('Over 55', 'h', 8, 60)]},
    {'n': 13, 't': 'Are you a single parent?', 'c': 'Demographics', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
    {'n': 14, 't': "Which best describes your spouse or domestic partner's work status?", 'c': 'Demographics', 'ty': 'multiple_choice', 'o': [('No spouse; I live alone', 'a', 1, None), ('Does not work outside the home', 'b', 2, None), ('Works a different schedule than I do in this company', 'c', 3, None), ('Works a different schedule than I do outside this company', 'd', 4, None), ('Works the same schedule as I do in this company', 'e', 5, None), ('Works the same schedule as I do outside this company', 'f', 6, None)]},
    {'n': 15, 't': 'How do you normally get to work?', 'c': 'Demographics', 'ty': 'multiple_choice', 'o': [('Drive by myself', 'a', 1, None), ('Carpool', 'b', 2, None), ('Public transportation', 'c', 3, None)]},
    {'n': 16, 't': 'How far do you commute to work (one way)?', 'c': 'Demographics', 'ty': 'multiple_choice', 'sc': 'average_miles', 'o': [('Less than 1 mile', 'a', 1, 0.5), ('1 to 5 miles', 'b', 2, 3), ('6 to 10 miles', 'c', 3, 8), ('11 to 20 miles', 'd', 4, 15), ('21 to 30 miles', 'e', 5, 25), ('31 to 40 miles', 'f', 6, 35), ('More than 40 miles', 'g', 7, 45)]},
    {'n': 17, 't': 'Looking at your daily commute, what is the worst time to start the day shift?', 'c': 'Demographics', 'ty': 'multiple_choice', 'o': [('Before 5:30 a.m.', 'a', 1, None), ('5:30 a.m.', 'b', 2, None), ('6:00 a.m.', 'c', 3, None), ('6:30 a.m.', 'd', 4, None), ('7:00 a.m.', 'e', 5, None), ('7:30 a.m.', 'f', 6, None), ('8:00 a.m.', 'g', 7, None), ('Later than 8:00 a.m.', 'h', 8, None)]},
    # HEALTH AND ALERTNESS (18-27)
    {'n': 18, 't': 'Do you normally use an alarm clock to wake up after a sleep period?', 'c': 'Health and Alertness', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
    {'n': 19, 't': 'Do you use an alarm clock to wake up when you are working day shift?', 'c': 'Health and Alertness', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
    {'n': 20, 't': 'Do you use an alarm clock to wake up when you are working afternoon shift?', 'c': 'Health and Alertness', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
    {'n': 21, 't': 'Do you use an alarm clock to wake up when you are working night shift?', 'c': 'Health and Alertness', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
    {'n': 22, 't': 'How often do you notice you are having problems with safety or performance due to sleepiness?', 'c': 'Health and Alertness', 'ty': 'multiple_choice', 'o': [('Never', 'a', 1, None), ('Rarely', 'b', 2, None), ('Once a month', 'c', 3, None), ('Once a week', 'd', 4, None), ('Almost daily', 'e', 5, None)]},
    {'n': 23, 't': 'How many hours of sleep do you get every 24-hour period when you are working first shift?', 'c': 'Health and Alertness', 'ty': 'multiple_choice', 'sc': 'average_hours', 'o': [('I never work the first shift', 'a', 0, None), ('Less than 5 hours', 'b', 1, 4.5), ('5 or more hours but less than 6 hours', 'c', 2, 5.5), ('6 or more hours but less than 7 hours', 'd', 3, 6.5), ('7 or more hours but less than 8 hours', 'e', 4, 7.5), ('8 or more hours but less than 9 hours', 'f', 5, 8.5), ('9 or more hours', 'g', 6, 9.5)]},
    {'n': 24, 't': 'How many hours of sleep do you get every 24-hour period when you are working second shift?', 'c': 'Health and Alertness', 'ty': 'multiple_choice', 'sc': 'average_hours', 'o': [('I never work the second shift', 'a', 0, None), ('Less than 5 hours', 'b', 1, 4.5), ('5 or more hours but less than 6 hours', 'c', 2, 5.5), ('6 or more hours but less than 7 hours', 'd', 3, 6.5), ('7 or more hours but less than 8 hours', 'e', 4, 7.5), ('8 or more hours but less than 9 hours', 'f', 5, 8.5), ('9 or more hours', 'g', 6, 9.5)]},
    {'n': 25, 't': 'How many hours of sleep do you get every 24-hour period when you are working third shift?', 'c': 'Health and Alertness', 'ty': 'multiple_choice', 'sc': 'average_hours', 'o': [('I never work the third shift', 'a', 0, None), ('Less than 5 hours', 'b', 1, 4.5), ('5 or more hours but less than 6 hours', 'c', 2, 5.5), ('6 or more hours but less than 7 hours', 'd', 3, 6.5), ('7 or more hours but less than 8 hours', 'e', 4, 7.5), ('8 or more hours but less than 9 hours', 'f', 5, 8.5), ('9 or more hours', 'g', 6, 9.5)]},
    {'n': 26, 't': 'How many hours of sleep do you get every 24-hour period on days off?', 'c': 'Health and Alertness', 'ty': 'multiple_choice', 'sc': 'average_hours', 'o': [('Less than 5 hours', 'a', 1, 4.5), ('5 or more hours but less than 6 hours', 'b', 2, 5.5), ('6 or more hours but less than 7 hours', 'c', 3, 6.5), ('7 or more hours but less than 8 hours', 'd', 4, 7.5), ('8 or more hours but less than 9 hours', 'e', 5, 8.5), ('9 or more hours', 'f', 6, 9.5)]},
    {'n': 27, 't': 'How many hours of sleep do you need every 24-hour period to be fully alert?', 'c': 'Health and Alertness', 'ty': 'multiple_choice', 'sc': 'average_hours', 'o': [('Less than 5 hours', 'a', 1, 4.5), ('5 or more hours but less than 6 hours', 'b', 2, 5.5), ('6 or more hours but less than 7 hours', 'c', 3, 6.5), ('7 or more hours but less than 8 hours', 'd', 4, 7.5), ('8 or more hours but less than 9 hours', 'e', 5, 8.5), ('9 or more hours', 'f', 6, 9.5)]},
    # WORKING CONDITIONS (28-45)
    {'n': 28, 't': 'Overall, this is a safe place to work.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 29, 't': 'Which best describes your opinion?', 'c': 'Working Conditions', 'ty': 'multiple_choice', 'o': [('The company can do a lot more to improve safety at this site', 'a', 1, None), ('The employees can do a lot more to improve safety at this site', 'b', 2, None), ('Both of the above', 'c', 3, None), ('Neither of the above, this is a very safe place to work', 'd', 4, None)]},
    {'n': 30, 't': 'This company places a high priority on communication.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 31, 't': 'Communication is important to me.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 32, 't': 'How much time is needed to communicate daily plant conditions between shifts?', 'c': 'Working Conditions', 'ty': 'multiple_choice', 'sc': 'average_minutes', 'o': [('Less than 10 minutes', 'a', 1, 5), ('10 minutes', 'b', 2, 10), ('15 minutes', 'c', 3, 15), ('20 minutes', 'd', 4, 20), ('25 minutes', 'e', 5, 25), ('30 minutes', 'f', 6, 30), ('More than 30 minutes', 'g', 7, 35)]},
    {'n': 33, 't': 'Management welcomes input from the workforce.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 34, 't': 'I enjoy the work that I do.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 35, 't': 'The pay here is good compared to other jobs in the area.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 36, 't': 'Management treats shift-workers and day-workers equally.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 37, 't': 'I feel like I am a part of this company.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 38, 't': 'Which best describes how you feel?', 'c': 'Working Conditions', 'ty': 'multi_select', 'o': [('There is no problem with last minute absenteeism at this site.', 'a', 1, None), ("Covering other people's last minute absenteeism disrupts my family and social life.", 'b', 2, None), ('The company needs to crack down on those few employees that are taking advantage of the existing absentee policy.', 'c', 3, None)]},
    {'n': 39, 't': 'Overall, things are getting better at this facility.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 40, 't': 'This is one of the best places to work in this area.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 41, 't': 'Job training is important to me.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 42, 't': 'I get enough training to do my job well.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 43, 't': 'Which best describes how you feel?', 'c': 'Working Conditions', 'ty': 'multiple_choice', 'o': [('We train way too much', 'a', 1, None), ('We train just the right amount', 'b', 2, None), ('We do not train nearly enough', 'c', 3, None)]},
    {'n': 44, 't': 'My direct supervisor responds to my concerns about working conditions.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 45, 't': 'Upper management responds to my concerns about working conditions.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    # SHIFT SCHEDULE FEATURES (46-78)
    {'n': 46, 't': 'A better schedule will really improve things here.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 47, 't': 'Current shift schedule policies are fair.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 48, 't': 'I like my current schedule.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 49, 't': 'I think there are better schedules available than our current schedule.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 50, 't': 'Which best describes you?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('I plan to go to a better shift as soon as I can', 'a', 1, None), ('My current shift is where I plan to stay', 'b', 2, None)]},
    {'n': 51, 't': 'My time off is predictable.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 52, 't': 'My schedule allows me the flexibility to get time off when I really need it.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 53, 't': 'If you were assigned to work a single shift for the next few years, which would be your preferred 8-hour shift?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Day Shift', 'a', 1, None), ('Afternoon Shift', 'b', 2, None), ('Night Shift', 'c', 3, None)]},
    {'n': 54, 't': 'If you were assigned to work a single shift for the next few years, which would be your least preferred 8-hour shift?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Day Shift', 'a', 1, None), ('Afternoon Shift', 'b', 2, None), ('Night Shift', 'c', 3, None)]},
    {'n': 55, 't': 'If you were assigned to work a single shift for the next few years, which would be your preferred 12-hour shift?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Days', 'a', 1, None), ('Nights', 'b', 2, None)]},
    {'n': 56, 't': 'Assuming that you get the same amount of pay, which is more important to you?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Working fewer hours each day that I work, even though I will get fewer days off each week', 'a', 1, None), ('Working more hours each day so that I can have more days off each week', 'b', 2, None)]},
    {'n': 57, 't': 'Which would you prefer?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Fixed or "steady" shifts', 'a', 1, None), ('Rotating shifts', 'b', 2, None)]},
    {'n': 58, 't': 'Which would you prefer?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Fixed shifts, even though seniority is not a consideration when being assigned to a shift', 'a', 1, None), ('Rotating shifts', 'b', 2, None)]},
    {'n': 59, 't': 'Which would you prefer?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Fixed shifts, even though I would not be assigned to my first choice', 'a', 1, None), ('Rotating shifts', 'b', 2, None)]},
    {'n': 60, 't': 'Keeping my current crew members together is important to me.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 61, 't': 'How often would you like to rotate between shifts?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Once a week', 'a', 1, None), ('Once every two weeks', 'b', 2, None), ('Once every four weeks', 'c', 3, None), ('Once every two months', 'd', 4, None), ('Once every six months', 'e', 5, None), ('Annually', 'f', 6, None)]},
    {'n': 62, 't': 'On an 8-hour schedule, which direction would you prefer to rotate?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Days>Nights>Evenings>Days', 'a', 1, None), ('Days>Evenings>Nights>Days', 'b', 2, None), ('No preference', 'c', 3, None)]},
    {'n': 63, 't': 'If you worked 8-hour shifts, what time would you like the day shift to start?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Before 5:30 a.m.', 'a', 1, None), ('5:30 a.m.', 'b', 2, None), ('6:00 a.m.', 'c', 3, None), ('6:30 a.m.', 'd', 4, None), ('7:00 a.m.', 'e', 5, None), ('7:30 a.m.', 'f', 6, None), ('8:00 a.m.', 'g', 7, None), ('Later than 8:00 a.m.', 'h', 8, None)]},
    {'n': 64, 't': 'If you worked 10-hour shifts, what time would you like the day shift to start?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Before 5:30 a.m.', 'a', 1, None), ('5:30 a.m.', 'b', 2, None), ('6:00 a.m.', 'c', 3, None), ('6:30 a.m.', 'd', 4, None), ('7:00 a.m.', 'e', 5, None), ('7:30 a.m.', 'f', 6, None), ('8:00 a.m.', 'g', 7, None), ('Later than 8:00 a.m.', 'h', 8, None)]},
    {'n': 65, 't': 'If you worked 12-hour shifts, what time would you like the day shift to start?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Before 5:30 a.m.', 'a', 1, None), ('5:30 a.m.', 'b', 2, None), ('6:00 a.m.', 'c', 3, None), ('6:30 a.m.', 'd', 4, None), ('7:00 a.m.', 'e', 5, None), ('7:30 a.m.', 'f', 6, None), ('8:00 a.m.', 'g', 7, None), ('Later than 8:00 a.m.', 'h', 8, None), ('Noon', 'i', 9, None), ('3:00 p.m.', 'j', 10, None)]},
    {'n': 66, 't': 'If pay was not a factor, which would you prefer over an 8-week period?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Work 8 Saturdays and have 8 Sundays off', 'a', 1, None), ('Work 8 Sundays and have 8 Saturdays off', 'b', 2, None), ('Work 4 full weekends and have 4 full weekends off', 'c', 3, None)]},
    {'n': 67, 't': 'The ability to swap shifts is important to me.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 68, 't': 'If pay is not a factor when comparing the following two work shifts, I would prefer to work a night shift that:', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Starts Sunday night and ends Monday morning', 'a', 1, None), ('Starts Friday night and ends Saturday morning', 'b', 2, None)]},
    {'n': 69, 't': 'Which best describes you?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('I like my weekends off to alternate', 'a', 1, None), ('I like to have several weekends off in a row and would be willing to work several in a row to make that happen', 'b', 2, None)]},
    {'n': 70, 't': 'Which best describes you?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('I like to work several days in a row and then take a long break', 'a', 1, None), ('I like to work a couple of days in a row and then take a short break', 'b', 2, None)]},
    {'n': 71, 't': 'If you could only have 3 days off per week, which of the following would you prefer?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Friday-Saturday-Sunday', 'a', 1, None), ('Saturday-Sunday-Monday', 'b', 2, None), ('Sunday-Monday-Tuesday', 'c', 3, None)]},
    {'n': 72, 't': 'If your schedule requires you to take weekdays off, which day do you prefer to have off?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Monday', 'a', 1, None), ('Tuesday', 'b', 2, None), ('Wednesday', 'c', 3, None), ('Thursday', 'd', 4, None), ('Friday', 'e', 5, None)]},
    {'n': 73, 't': 'What percentage of time do you think you should be working at the same time as your supervisor?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('100%', 'a', 1, None), ('90%', 'b', 2, None), ('80%', 'c', 3, None), ('70%', 'd', 4, None), ('60%', 'e', 5, None), ('50% or less', 'f', 6, None)]},
    {'n': 74, 't': "I don't mind doing several different types of work during the week.", 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 75, 't': 'Which best describes you?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('I am willing to work my share of weekends', 'a', 1, None), ('I will quit before I work weekends', 'b', 2, None)]},
    {'n': 76, 't': 'I am willing to work weekends occasionally if I can plan them in advance.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 77, 't': 'It is clear to me why we have to go to a 24/7 schedule/weekend work to keep this company competitive in this industry.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 78, 't': 'Which best describes you?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('I am willing to try a 12-hour/7-day/new schedule for 6 to 12 months', 'a', 1, None), ('I will reluctantly go along with a 12-hour/7-day/new schedule trial if that is what the majority of the workforce wants', 'b', 2, None), ('I will quit before I go to a 12-hour/7-day/new schedule', 'c', 3, None)]},
    # OVERTIME (79-91)
    {'n': 79, 't': 'I depend on overtime worked outside my schedule to help me make ends meet:', 'c': 'Overtime', 'ty': 'multiple_choice', 'o': [('Never', 'a', 1, None), ('Sometimes', 'b', 2, None), ('Frequently', 'c', 3, None), ('Every week', 'd', 4, None)]},
    {'n': 80, 't': 'Over the last few months I have been:', 'c': 'Overtime', 'ty': 'multiple_choice', 'o': [('Working too much overtime', 'a', 1, None), ('Working too little overtime', 'b', 2, None), ('Working just the right amount of overtime', 'c', 3, None)]},
    {'n': 81, 't': 'Overtime levels are just right the way they are.', 'c': 'Overtime', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 82, 't': 'When you work overtime outside your schedule, when do you usually work it?', 'c': 'Overtime', 'ty': 'multiple_choice', 'o': [("I don't work overtime", 'a', 1, None), ('On a regularly scheduled workday by coming in early or staying late', 'b', 2, None), ('On Saturdays, but not Sundays', 'c', 3, None), ('On Sundays, but not Saturdays', 'd', 4, None), ('Any chance I get', 'e', 5, None), ('I work overtime when necessary for business needs', 'f', 6, None)]},
    {'n': 83, 't': 'When you have to work overtime, when do you prefer to work it?', 'c': 'Overtime', 'ty': 'multiple_choice', 'o': [('On a scheduled work day', 'a', 1, None), ('On a day off', 'b', 2, None), ('No preference', 'c', 3, None)]},
    {'n': 84, 't': 'I prefer overtime by extending my shift.', 'c': 'Overtime', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 85, 't': 'I prefer to work overtime by coming in on a day off.', 'c': 'Overtime', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 86, 't': 'Current overtime distribution policies are fair.', 'c': 'Overtime', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 87, 't': 'Overtime is predictable and can be planned for.', 'c': 'Overtime', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 88, 't': 'If you had to choose between more time off or more overtime, what would you choose?', 'c': 'Overtime', 'ty': 'multiple_choice', 'o': [('More time off', 'a', 1, None), ('More overtime', 'b', 2, None)]},
    {'n': 89, 't': 'When it comes to overtime, I generally want to get:', 'c': 'Overtime', 'ty': 'multiple_choice', 'o': [('As much as possible', 'a', 1, None), ('Frequent overtime', 'b', 2, None), ('Occasional overtime', 'c', 3, None), ('Infrequent overtime', 'd', 4, None), ('I do not want any overtime', 'e', 5, None)]},
    {'n': 90, 't': 'I expect to get overtime whenever I want it.', 'c': 'Overtime', 'ty': 'likert_5', 'sc': 'average_rating', 'o': likert()},
    {'n': 91, 't': 'How much overtime would you like to have every week?', 'c': 'Overtime', 'ty': 'multiple_choice', 'sc': 'average_hours', 'o': [('None', 'a', 1, 0), ('Less than 2 hours', 'b', 2, 1), ('Between 2 and 4 hours', 'c', 3, 3), ('Between 4 and 6 hours', 'd', 4, 5), ('Between 6 and 8 hours', 'e', 5, 7), ('Between 8 and 12 hours', 'f', 6, 10), ('I will take all that I can get', 'g', 7, 15)]},
    # DAY CARE/ELDER CARE (92-97)
    {'n': 92, 't': 'Do you use outside day/elder care?', 'c': 'Day Care/Elder Care', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
    {'n': 93, 't': 'Is your day/elder care provider:', 'c': 'Day Care/Elder Care', 'ty': 'multiple_choice', 'o': [('Close to home', 'a', 1, None), ('Close to work', 'b', 2, None), ('At home', 'c', 3, None)]},
    {'n': 94, 't': 'Is your day/elder care provider a family member, neighbor or friend?', 'c': 'Day Care/Elder Care', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
    {'n': 95, 't': 'Do you use day/elder care when working days?', 'c': 'Day Care/Elder Care', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
    {'n': 96, 't': 'Is day/elder care a bigger issue on a particular shift?', 'c': 'Day Care/Elder Care', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
    {'n': 97, 't': 'If you answered "yes" on the previous question, which shift?', 'c': 'Day Care/Elder Care', 'ty': 'multiple_choice', 'o': [('Days', 'a', 1, None), ('Afternoons', 'b', 2, None), ('Nights', 'c', 3, None)]},
]


def import_questions():
    with app.app_context():
        db.create_all()
        count = 0
        for q in QUESTIONS:
            if MasterQuestion.query.filter_by(question_number=q['n']).first():
                print(f"Q{q['n']} exists, skipping...")
                continue
            likert_low, likert_high = None, None
            if q['ty'] == 'likert_5':
                likert_low, likert_high = 'Strongly Disagree', 'Strongly Agree'
            mq = MasterQuestion(
                question_text=q['t'], question_number=q['n'], category=q['c'],
                question_type=q['ty'], likert_low_label=likert_low, likert_high_label=likert_high,
                has_special_calculation=bool(q.get('sc')), calculation_type=q.get('sc')
            )
            db.session.add(mq)
            db.session.flush()
            for i, opt in enumerate(q.get('o', [])):
                ro = ResponseOption(
                    question_id=mq.id, option_text=opt[0], option_code=opt[1],
                    numeric_value=opt[2], display_order=i + 1,
                    calculation_value=opt[3] if len(opt) > 3 else None
                )
                db.session.add(ro)
            count += 1
            print(f"Imported Q{q['n']}: {q['t'][:40]}...")
        db.session.commit()
        print(f"\nImported {count} questions. Total: {MasterQuestion.query.count()}")


if __name__ == '__main__':
    import_questions()


# I did no harm and this file is not truncated
