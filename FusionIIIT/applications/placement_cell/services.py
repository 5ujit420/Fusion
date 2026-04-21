from .selectors import get_placement_years, get_placement_records_summary, get_student_records_with_department

def calculate_placement_statistics():
    years = get_placement_years()
    records = get_placement_records_summary()
    studentrecord = get_student_records_with_department()
    
    tcse = {}
    tece = {}
    tme = {}
    tadd = {}
    
    for r in records:
        r['name__count'] = 0
        r['year__count'] = 0
        r['placement_type__count'] = 0
        
    for y in years:
        year = y['year']
        tcse[year] = 0
        tece[year] = 0
        tme[year] = 0
        
        for r in records:
            if r['year'] == year and r['placement_type'] != "HIGHER STUDIES":
                for z in studentrecord:
                    # Fix for CS-06 and CS-07: Using pre-fetched related objects instead of multiple queries
                    if z.record_id.name == r['name'] and z.record_id.year == r['year']:
                        try:
                            dept = z.unique_id.id.department.name
                            if dept == "CSE":
                                tcse[year] += 1
                                r['name__count'] += 1
                            elif dept == "ECE":
                                tece[year] += 1
                                r['year__count'] += 1
                            elif dept == "ME":
                                tme[year] += 1
                                r['placement_type__count'] += 1
                        except AttributeError:
                            pass # Safety catch for inconsistent data
                            
        tadd[year] = tcse[year] + tece[year] + tme[year]
        y['year__count'] = [tadd[year], tcse[year], tece[year], tme[year]]
        
    return years, records
