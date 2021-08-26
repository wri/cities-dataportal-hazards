#!/usr/bin/env python
# coding: utf-8

# In[ ]:

import ee
ee.Initialize()
from datetime import date, timedelta
from calendar import isleap

PR_99 = ee.ImageCollection('users/tedwongwri/dataportal/percentiles/pr_99').map(lambda i: i.multiply(86400))
TASMAX_99 = ee.ImageCollection('users/tedwongwri/dataportal/percentiles/tasmax_99').map(lambda i: i.add(273.15))
TASMIN_01 = ee.ImageCollection('users/tedwongwri/dataportal/percentiles/tasmin_01').map(lambda i: i.add(273.15))

NOLEAP_MODELS = ['bcc-csm1-1', 'BNU-ESM', 'CanESM2', 'CCSM4', 'CESM1-BGC', 'CSIRO-Mk3-6-0', 'GFDL-CM3', 'GFDL-ESM2G', 'GFDL-ESM2M', 'inmcm4', 'IPSL-CM5A-LR', 'IPSL-CM5A-MR', 'MIROC5', 'NorESM1-M']

def skipleap(d, model):
    # Checks whether d is Feb 29. If not, returns d. If it is and model in list of leap-intolerant models, returns March 1.
    if model in NOLEAP_MODELS and d.month == 2 and d.day == 29:
        return date(d.year, 3, 1)
    else:
        return d

def ds(vardata, year, model=None, is_nex=True):
	yeardata = vardata.filterDate(str(year) + '-01-01', str(year) + '-12-31')
	if is_nex:
		yeardata = yeardata.filterMetadata('scenario', 'equals', ['historical', 'rcp85'][(year > 2005) * 1])
	dry_days = yeardata.map(lambda d: d.eq(0).multiply(1))
	return process_runs(dry_days, 5, 'count')

def ece(vardata, year, model=None, is_nex=True):
    return

def ehe(vardata, year, model=None, is_nex=True):
	yeardata = vardata.filterDate(str(year) + '-01-01', str(year) + '-12-31')
	if is_nex:
		yeardata = yeardata.filterMetadata('scenario', 'equals', ['historical', 'rcp85'][(year > 2005) * 1])
	if model:
		tasmax_p99_model = TASMAX_99.filterMetadata('model', 'equals', model).first()
	else:
		tasmax_p99_model = TASMAX_99.mean()
	over_year = yeardata.map(lambda x: x.gt(tasmax_p99_model).multiply(1))
	return over_year.sum()

def mtt35(vardata, year, model=None, is_nex=True):
	yeardata = vardata.filterDate(str(year) + '-01-01', str(year) + '-12-31')
	if is_nex:
		yeardata = yeardata.filterMetadata('scenario', 'equals', ['historical', 'rcp85'][(year > 2005) * 1])
	over_year = yeardata.map(lambda x: x.gt(35 + 273.15).multiply(1))
	return over_year.sum()

def maxdryspell(vardata, year, model=None, is_nex=True):
    # Climdex CDD: Let RR_ij be the daily precipitation amount on day i in period j. Count the largest number of consecutive days where RR_ij < 1mm
	yeardata = vardata.filterDate(str(year) + '-01-01', str(year) + '-12-31')
	if is_nex:
		yeardata = yeardata.filterMetadata('scenario', 'equals', ['historical', 'rcp85'][(year > 2005) * 1])
	dry_days = yeardata.map(lambda d: d.multiply(86400).eq(0))
	return process_runs(dry_days, 1, 'max')

def epe(vardata, year, model=None, is_nex=True):
	yeardata = vardata.filterDate(str(year) + '-01-01', str(year) + '-12-31')
	if is_nex:
		yeardata = yeardata.filterMetadata('scenario', 'equals', ['historical', 'rcp85'][(year > 2005) * 1]).map(lambda i: i.multiply(86400))
	else:
		yeardata = yeardata.map(lambda i: i.multiply(0.011574074074074073).multiply(86400))
	if model:
		pr_p99_model = PR_99.filterMetadata('model', 'equals', model).first()
	else:
		pr_p99_model = PR_99.mean()
	over_year = yeardata.map(lambda x: x.gt(pr_p99_model).multiply(1))
	return over_year.sum()
	
def totalprecip(vardata, year, model=None, is_nex=True):
	yeardata = vardata.filterDate(str(year) + '-01-01', str(year) + '-12-31')
	if is_nex:
		yeardata = yeardata.filterMetadata('scenario', 'equals', ['historical', 'rcp85'][(year > 2005) * 1]).map(lambda i: i.multiply(86400))
	else:
		yeardata = yeardata.map(lambda i: i.multiply(0.011574074074074073).multiply(86400))
	return yeardata.sum()
	
def maxprecip(vardata, year, model=None, is_nex=True):
	yeardata = vardata.filterDate(str(year) + '-01-01', str(year) + '-12-31')
	if is_nex:
		yeardata = yeardata.filterMetadata('scenario', 'equals', ['historical', 'rcp85'][(year > 2005) * 1]).map(lambda i: i.multiply(86400))
	else:
		yeardata = yeardata.map(lambda i: i.multiply(0.011574074074074073).multiply(86400))
	return yeardata.max()

susc = ee.Image("users/tedwongwri/dataportal/landslide/susc")
ari95 = ee.Image("users/tedwongwri/dataportal/landslide/ARI95")
def modlandslide(vardata, year, model=None, is_nex=True):
# Returns number of days in year with moderate or high landslide risk
# antecedent rainfall index from https://agupubs.onlinelibrary.wiley.com/doi/full/10.1002/2017EF000715
	start_date, end_date = date(year, 1, 1), date(year, 12, 31)
	modeldata = vardata.filterDate((start_date - timedelta(days=7)).isoformat(), end_date.isoformat())
	modrisk_list = ee.List([]) # holds results
	precip_list = ee.List([ee.Image(0)]) # holds input precip for current date and six previous; zero image is dummy, will be removed immediately
	for t in range(6):  # Create list with seven days of data, with most recent last
		tt = 6 - t
		tdate = start_date - timedelta(days=tt)
		if is_nex:
			modelscenario_data = modeldata.filterMetadata('scenario', 'equals', ['historical', 'rcp85'][(tdate.year > 2005) * 1])
			precip_list = precip_list.add(modelscenario_data.filterDate(tdate.isoformat(), (tdate + timedelta(days=1)).isoformat()).first().multiply(864000)) # ARI map based on data w precip measured as 0.1mm/day
		else:
			precip_list = precip_list.add(modeldata.filterDate(tdate.isoformat(), (tdate + timedelta(days=1)).isoformat()).first().multiply(10000))
	for datediff in range((end_date - start_date).days + ([0, -1][(isleap(year) and model in NOLEAP_MODELS) * 1])):
		focal_date = skipleap(start_date + timedelta(days = datediff), model)
		if is_nex:
			modelscenario_data = modeldata.filterMetadata('scenario', 'equals', ['historical', 'rcp85'][(focal_date.year > 2005) * 1])
		precip_list = precip_list.slice(1, 7)  #Every day remove one, add one
		if is_nex:
			precip_list = precip_list.add(modelscenario_data.filterDate(focal_date.isoformat(), (skipleap(focal_date + timedelta(days=1), model)).isoformat()).first().multiply(864000))
		else:
			precip_list = precip_list.add(modeldata.filterDate(focal_date.isoformat(), (skipleap(focal_date + timedelta(days=1), model)).isoformat()).first().multiply(10000))
		numerator = ee.Image.constant(0)
		denominator = ee.Image.constant(0)
		for t in range(7):
			tdate = skipleap(focal_date - timedelta(days=t), model)
			precip = ee.Image(precip_list.get(-(t + 1)))
			w = 1.0 / ((t + 1)**2)
			numerator = numerator.add(precip.multiply(w))
			denominator = denominator.add(w)
		modrisk_list = modrisk_list.add((numerator.divide(denominator).gt(ari95).multiply(1)).multiply(susc.gt(2).multiply(1)))
	return ee.ImageCollection(modrisk_list).sum()
    
def highlandslide(vardata, year, model=None, is_nex=True):
# Returns number of days in year with moderate or high landslide risk
# antecedent rainfall index from https://agupubs.onlinelibrary.wiley.com/doi/full/10.1002/2017EF000715
	start_date, end_date = date(year, 1, 1), date(year, 12, 31)
	modeldata = vardata.filterDate((start_date - timedelta(days=7)).isoformat(), end_date.isoformat())
	highrisk_list = ee.List([]) # holds results
	precip_list = ee.List([ee.Image(0)]) # holds input precip for current date and six previous; zero image is dummy, will be removed immediately
	for t in range(6):  # Create list with seven days of data, with most recent last
		tt = 6 - t
		tdate = start_date - timedelta(days=tt)
		if is_nex:
			modelscenario_data = modeldata.filterMetadata('scenario', 'equals', ['historical', 'rcp85'][(tdate.year > 2005) * 1])
			precip_list = precip_list.add(modelscenario_data.filterDate(tdate.isoformat(), (tdate + timedelta(days=1)).isoformat()).first().multiply(864000))
		else:
			precip_list = precip_list.add(modeldata.filterDate(tdate.isoformat(), (tdate + timedelta(days=1)).isoformat()).first().multiply(10000))
	for datediff in range((end_date - start_date).days + ([0, -1][(isleap(year) and model in NOLEAP_MODELS) * 1])):
		focal_date = skipleap(start_date + timedelta(days = datediff), model)
		if is_nex:
			modelscenario_data = modeldata.filterMetadata('scenario', 'equals', ['historical', 'rcp85'][(focal_date.year > 2005) * 1])
		precip_list = precip_list.slice(1, 7)  #Every day remove one, add one
		if is_nex:
			precip_list = precip_list.add(modelscenario_data.filterDate(focal_date.isoformat(), (skipleap(focal_date + timedelta(days=1), model)).isoformat()).first().multiply(864000))
		else:
			precip_list = precip_list.add(modeldata.filterDate(focal_date.isoformat(), (skipleap(focal_date + timedelta(days=1), model)).isoformat()).first().multiply(10000))
		numerator = ee.Image.constant(0)
		denominator = ee.Image.constant(0)
		for t in range(7):
			tdate = skipleap(focal_date - timedelta(days=t), model)
			precip = ee.Image(precip_list.get(-(t + 1)))
			w = 1.0 / ((t + 1)**2)
			numerator = numerator.add(precip.multiply(w))
			denominator = denominator.add(w)
		highrisk_list = highrisk_list.add((numerator.divide(denominator).gt(ari95).multiply(1)).multiply(susc.gt(4).multiply(1)))
	return ee.ImageCollection(highrisk_list).sum()
    

hazards = [
            {
             'name': 'ds',
             'definition': ds,
             'variable': 'pr',
             'num_bins': 100,
             'bin_width': 1,
			 'use_greaterthan': True
            },
            {
             'name': 'maxdryspell',
             'definition': maxdryspell,
             'variable': 'pr',
             'num_bins': 73,
             'bin_width': 5,
			 'use_greaterthan': True
            },
            {
             'name': 'mtt35',
             'definition': mtt35,
             'variable': 'tasmax',
             'num_bins': 74,
             'bin_width': 5,
			 'use_greaterthan': True
            },
            {
             'name': 'modlandslide', 
             'definition': modlandslide,
             'variable': 'pr',
             'num_bins': 60,
             'bin_width': 5,
			 'use_greaterthan': True
            },
            {
             'name': 'highlandslide',
             'definition': highlandslide,
             'variable': 'pr',
             'variable': 'pr',
             'num_bins': 60,
             'bin_width': 5,
			 'use_greaterthan': True
            },
            {
             'name': 'epe',
             'definition': epe,
             'variable': 'pr',
             'num_bins': 100,
             'bin_width': 1,
			 'use_greaterthan': True
            },
            {
             'name': 'totalprecip',
             'definition': totalprecip,
             'variable': 'pr',
             'num_bins': 85,
             'bin_width': 100,
			 'use_greaterthan': True
            },
            {
             'name': 'maxprecip',
             'definition': maxprecip,
             'variable': 'pr',
             'num_bins': 80,
             'bin_width': 20,
			 'use_greaterthan': True
            }
]

def process_runs(imgs, runLength, resultType): 
# from Logan Byers
    def doOne(img, data):
   #data = ee.Image(data);

        dataDict = ee.Dictionary(data)

        previousThresholdImage = ee.Image(dataDict.get('previousThresholdImage'))
        currentStreakImage = ee.Image(dataDict.get('currentStreakImage')).uint16()
        streakCountImage = ee.Image(dataDict.get('streakCountImage')).uint16()
        longestStreakImage = ee.Image(dataDict.get('longestStreakImage')).uint16()
        streakAccumulation = ee.Image(dataDict.get('streakAccumulation')).uint16()
        numRemaining = ee.Number(dataDict.get('numRemaining'))

        # WHERE yesterday AND today : 1, else 0
        #continueStreakImage = previousThresholdImage.and(ee.Image(img))
        continueStreakImage = previousThresholdImage.multiply(ee.Image(img)).multiply(ee.Image(numRemaining).gt(1).multiply(1))

        # WHERE NOT on streak :  yesterday streak length, else 0
        #streakEndedImage = currentStreakImage.multiply(currentStreakImage.and(continueStreakImage.not()))
        streakEndedImage = currentStreakImage.multiply(currentStreakImage.multiply(continueStreakImage.multiply(-1).add(1)))

        # WHERE NOT on streak AND yesterday streak length > length threshold : 1, else 0
        endedStreakExceedsLengthImage = currentStreakImage.multiply(streakEndedImage).gte(runLength)

        # update the state
        accumulator = ee.Dictionary.fromLists([
            'previousThresholdImage',
            'currentStreakImage',
            'streakCountImage',
            'longestStreakImage',
            'streakAccumulation',
            'numRemaining'
          ], [
            # previousThresholdImage --> today's image
            ee.Image(img),
            # currentStreakImage --> today's image PLUS yesterday's streak (where continuing)
            currentStreakImage
              .multiply(continueStreakImage).add(ee.Image(img)),
            # streakCountImage --> PLUS 1 where long streak ended today
            streakCountImage.add(endedStreakExceedsLengthImage),
            # longestStreakImage --> larger of prev and current value
            longestStreakImage.max(currentStreakImage.multiply(continueStreakImage).add(ee.Image(img))),
            # streakAccumulation --> yesterday's accum plus current 1/0, if in streak
            streakAccumulation.add(ee.Image(img).multiply(continueStreakImage)),
            # numRemaining --> minus 1
            numRemaining.add(-1)
          ]
        )

        return accumulator
  
    resultImageName = {
        'count': 'streakCountImage',
        'max': 'longestStreakImage',
        'accum': 'streakAccumulation'
    }
  
    streakData = imgs.iterate(
    # iterate over each image in the ImageCollection
    #   accumulate a stateful Dictionary of images
    
        doOne, ee.Dictionary.fromLists([
          'previousThresholdImage', 
          'currentStreakImage',
          'streakCountImage',
          'longestStreakImage',
          'streakAccumulation',
          'numRemaining'
        ], [
          ee.Image.constant(1),
          ee.Image.constant(0).uint16(),
          ee.Image.constant(0).uint16(),
          ee.Image.constant(0).uint16(),
          ee.Image.constant(0).uint16(),
          imgs.size().add(-1)
        ]
        )
    
    )
    return ee.Image(ee.Dictionary(streakData).get(resultImageName[resultType]))