/// Gestion des temps dans timeline.js

/**
 * Returns a formatted label for the landmark's time, considering both creation and disappearance times.
 * @param {Object} appTime - Object representing the creation time
 * @param {Object} disTime - Object representing the disappearance time
 * @param {string} lang - Language code for label translation
 * @returns {string} Formatted time label
 */
function getValidTimeForLandmarkLabel(appTime, disTime, lang){

  var appTimeLabels = {"en": "Creation time", "fr": "Date de création"} ;
  var disTimeLabels = {"en": "Disappearance time", "fr": "Date de disparition"} ;
  var betweenLabels = {"en": "between", "fr": "entre"} ;
  var beforeLabels = {"en": "before", "fr": "avant"} ;
  var afterLabels = {"en": "after", "fr": "après"} ;
  var andLabels = {"en": "and", "fr": "et"} ;

  var appTimeLabel = "<b>" + (appTimeLabels[lang] || appTimeLabels["en"]) + ":</b>" ;
  var disTimeLabel = "<b>" + (disTimeLabels[lang] || disTimeLabels["en"]) + ":</b>" ;
  var betweenLabel = betweenLabels[lang] || betweenLabels["en"] ;
  var beforeLabel = beforeLabels[lang] || beforeLabels["en"] ;
  var afterLabel = afterLabels[lang] || afterLabels["en"] ;
  var andLabel = andLabels[lang] || andLabels["en"] ;
  var label = "" ;

  if (appTime.precise){
    label += `<div>${appTimeLabel}${appTime.precise.label}</div>` ;
  } else if (appTime.before && appTime.after){
    label += `<div>${appTimeLabel} ${betweenLabel} ${appTime.before.label} ${andLabel} ${appTime.after.label}</div>` ;
  } else if (appTime.before){
    label += `<div>${appTimeLabel} ${beforeLabel} ${appTime.before.label}</div>` ;
  } else if (appTime.after){
    label += `<div>${appTimeLabel} ${afterLabel} ${appTime.after.label}</div>` ;
  }

  var spacing = "50px" ;
  label += `<div style="margin-left: ${spacing} 0;">-</div>`;

  if (disTime.precise){
    label += `<div>${disTimeLabel}${disTime.precise.label}</div>` ;
  } else if (disTime.before && disTime.after){
    label += `<div>${disTimeLabel} ${betweenLabel} ${disTime.before.label} ${andLabel} ${disTime.after.label}</div>` ;
  } else if (disTime.before){
    label += `<div>${disTimeLabel} ${beforeLabel} ${disTime.before.label}</div>` ;
  } else if (disTime.after){
    label += `<div>${disTimeLabel} ${afterLabel} ${disTime.after.label}</div>` ;
  }

  return label

}

function getLabelContext(timeStamp, timePrecision) {
  const timeElems = extractElementsFromTimeStamp(timeStamp);
  const precision = extractElementsFromTimePrecision(timePrecision);
  const year = parseInt(timeElems.year);

  return {
    ...timeElems,
    year,
    precision,
    // Calculs universels
    century: Math.ceil(year / 100),
    millennium: Math.ceil(year / 1000),
    decade: Math.trunc(year / 10) * 10,
    dayInt: parseInt(timeElems.day),
    monthInt: parseInt(timeElems.month)
  };
}

function formatFrenchTimeLabel(ctx) {
  const months = { 
    1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin", 
    7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre" 
  };
  
  const monthName = months[ctx.monthInt];

  switch (ctx.precision) {
    case "millenium": {
      const suffix = ctx.millennium === 1 ? "re" : "e";
      return `${ctx.millennium}${suffix} millénaire`;
    }

    case "century": {
      const suffix = ctx.century === 1 ? "er" : "e";
      return `${ctx.century}${suffix} siècle`;
    }

    case "decade":
      return `années ${ctx.decade}`;

    case "year":
      return `${ctx.year}`;

    case "month":
      return `${monthName} ${ctx.year}`;

    case "day":
    case "hours":
    case "minutes":
    case "seconds":
    case "milliseconds": {
      const dayLabel = ctx.dayInt === 1 ? "1er" : ctx.day;
      return `${dayLabel} ${monthName} ${ctx.year}`;
    }

    default:
      return `${ctx.year}`;
  }
}

function formatEnglishLabel(ctx) {
  const months = { 
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June", 
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December" 
  };

  // Fonction interne pour gérer les suffixes (1st, 2nd, 3rd, 4th...)
  const getOrdinal = (n) => {
    const s = ["th", "st", "nd", "rd"];
    const v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
  };

  const monthName = months[ctx.monthInt];

  switch (ctx.precision) {
    case "millenium":
      return `${getOrdinal(ctx.millennium)} millennium`;

    case "century":
      return `${getOrdinal(ctx.century)} century`;

    case "decade":
      return `${ctx.decade}s`; // ex: 1990s

    case "year":
      return `${ctx.year}`;

    case "month":
      return `${monthName} ${ctx.year}`;

    case "day":
    case "hours":
    case "minutes":
    case "seconds":
    case "milliseconds":
      // Format standard "Month Day, Year"
      return `${monthName} ${ctx.day}, ${ctx.year}`;

    default:
      return `${ctx.year}`;
  }
}

function getTimeWithLabel(timeStamp, timePrecision, formatterFn) {
  // On récupère les informations calculées
  var context = getLabelContext(timeStamp, timePrecision);

  // On génère le label en utilisant la fonction de langue passée en paramètre
  var label = formatterFn(context);

  // On retourne l'objet enrichi
  return {
    ...context,
    label
  };
}

function getTimeWithLangLabel(timeStamp, timePrecision, lang){
  if (lang === "fr"){
    return getTimeWithLabel(timeStamp, timePrecision, formatFrenchTimeLabel);
  }else if (lang === "en"){
    return getTimeWithLabel(timeStamp, timePrecision, formatEnglishLabel);
  }else {
    // Par défaut, on retourne le label en anglais
    return getTimeWithLabel(timeStamp, timePrecision, formatEnglishLabel);
  }
}

function createTimelineTime(year=null, month=null, day=null, hour=null, minute=null, second=null, millisecond=null, format=null){
  year = (!year) ? '' : year ;
  month = (!month) ? '' : month ;
  day = (!day) ? '' : day ;
  hour = (!hour) ? '' : hour ;
  minute = (!minute) ? '' : minute ;
  second = (!second) ? '' : second ;
  millisecond = (!millisecond) ? '' : millisecond ;
  format = (!format) ? '' : format ;
  return {year, month, day, hour, minute, second, millisecond, format}
}

function createTime(timeStamp, timePrecision){
  var timeElems = extractElementsFromTimeStamp(timeStamp) ;
  var precision = extractElementsFromTimePrecision(timePrecision) ;
  timeElems = correctTimeAccordingPrecision(timeElems, precision) ;

  var time = createTimelineTime(timeElems.year, timeElems.month, timeElems.day, timeElems.hour, timeElems.minute, timeElems.second, timeElems.millisecond, timeElems.format) ;
  return time
}

function createTimeFromTwoTimes(timeStamp1, timePrecision1, timeStamp2, timePrecision2){
  var time1 = getDateObjectFromTimeStamp(timeStamp1) ;
  var time2 = getDateObjectFromTimeStamp(timeStamp2) ;
  var meanTimes = getMeanOfTwoTimes(time1, time2);
  var meanTimesElems = extractElementsFromTime(meanTimes);
  var precision = "day" ;
  meanTimesElems = correctTimeAccordingPrecision(meanTimesElems, precision) ;
  var time = createTimelineTime(meanTimesElems.year, meanTimesElems.month, meanTimesElems.day,
    meanTimesElems.hour, meanTimesElems.minute, meanTimesElems.second, meanTimesElems.millisecond,
    meanTimesElems.format) ;
  return time
}

function correctTimeAccordingPrecision(time, precision){
  time.format = null ;

  if (precision == "year"){
    time.month = time.day = time.hour = time.minute = time.second = time.millisecond = null;
  }else if (precision == "month"){
    time.day = time.hour = time.minute = time.second = time.millisecond = null;
  }else if (precision == "day"){
    time.hour = time.minute = time.second = time.millisecond = null;
  }

  return time
}

function getMeanOfTwoTimes(time1, time2){
  var intTime1 = time1.getTime() ;
  var intTime2 = time2.getTime() ;
  var meanIntTimes = (intTime1 + intTime2) / 2 ;
  var meanTimes = new Date(meanIntTimes) ;
  return meanTimes ;
}

function getMeanOfTwoTimesFromStamps(timeStamp1, timeStamp2){
  var formattedTimeStamp1 = timeStamp1.replace("+",""); // Retirer le +
  var formattedTimeStamp2 = timeStamp2.replace("+",""); // Retirer le +
  var time1 = new Date(formattedTimeStamp1); // Créer un objet Date
  var time2 = new Date(formattedTimeStamp2); // Créer un objet Date
  return getMeanOfTwoTimes(time1, time2);
}

function extractElementsFromTimePrecision(timePrecision) {
  var map = {
    "http://www.w3.org/2006/time#unitDay": "day",
    "http://www.w3.org/2006/time#unitMonth": "month",
    "http://www.w3.org/2006/time#unitYear": "year",
    "http://www.w3.org/2006/time#unitDecade": "decade",
    "http://www.w3.org/2006/time#unitCentury": "century",
    "http://www.w3.org/2006/time#unitMillenium": "millenium"
  };

  return map[timePrecision] || null;
}

function getDateObjectFromTimeStamp(timeStamp){
  // Convertir la chaîne en un objet datetime
  // Note : le "Z" indique UTC (temps universel coordonné), donc on l'enlève avec replace
  // var formattedTimeStamp = timeStamp.replace("Z", "").replace("+",""); // Retirer le "Z" et le +
  var formattedTimeStamp = timeStamp.replace("+",""); // Retirer le +
  var date = new Date(formattedTimeStamp); // Créer un objet Date
  return date;
}

function extractElementsFromTimeStamp(timeStamp){
  var time = getDateObjectFromTimeStamp(timeStamp);
  return extractElementsFromTime(time);
}

function extractElementsFromTime(time){
  // Récupérer les différentes parties
  var year = String(time.getUTCFullYear());      // Année
  var month = String(time.getUTCMonth() + 1);   // Mois (commence à 0, donc ajouter 1)
  var day = String(time.getUTCDate());          // Jour
  var hours = String(time.getUTCHours());       // Heures
  var minutes = String(time.getUTCMinutes());   // Minutes
  var seconds = String(time.getUTCSeconds());   // Secondes
  var milliseconds = String(time.getUTCMilliseconds()); // Millisecondes
  return { year, month, day, hours, minutes, seconds, milliseconds }
}

function getValidTimeForLandmark(timeApp={}, timeDis={}, timeBeforeApp={}, timeAfterApp={}, timeBeforeDis={}, timeAfterDis={}, lang="en"){
  var startTime = {} ;
  var startTimePrec = undefined ;
  var startTimeBefore = undefined ;
  var startTimeAfter = undefined ;
  if(timeApp.stamp && timeApp.precision){
    var startTimePrec = getTimeWithLangLabel(timeApp.stamp.value, timeApp.precision.value, lang) ;
    startTime.precise = startTimePrec ;
  }else if(timeBeforeApp.stamp && timeBeforeApp.precision && timeAfterApp.stamp && timeAfterApp.precision){
    var startTimeBefore = getTimeWithLangLabel(timeBeforeApp.stamp.value, timeBeforeApp.precision.value, lang) ;
    var startTimeAfter = getTimeWithLangLabel(timeAfterApp.stamp.value, timeAfterApp.precision.value, lang) ;
    startTime.before = startTimeBefore ;
    startTime.after = startTimeAfter ;
  }else if (timeBeforeApp.stamp && timeBeforeApp.precision){
    var startTimeBefore = getTimeWithLangLabel(timeBeforeApp.stamp.value, timeBeforeApp.precision.value, lang) ;
    startTime.before = startTimeBefore ;
  }else if (timeAfterApp.stamp && timeAfterApp.precision){
    var startTimeAfter = getTimeWithLangLabel(timeAfterApp.stamp.value, timeAfterApp.precision.value, lang) ;
    startTime.after = startTimeAfter ;
  }

  var endTime = {} ;
  if(timeDis.stamp && timeDis.precision){
    var endTimePrec = getTimeWithLangLabel(timeDis.stamp.value, timeDis.precision.value, lang) ;
    endTime.precise = endTimePrec ;
  }else if(timeBeforeDis.stamp && timeBeforeDis.precision && timeAfterDis.stamp && timeAfterDis.precision){
    var endTimeBefore = getTimeWithLangLabel(timeBeforeDis.stamp.value, timeBeforeDis.precision.value, lang) ;
    var endTimeAfter = getTimeWithLangLabel(timeAfterDis.stamp.value, timeAfterDis.precision.value, lang) ;
    endTime.before = endTimeBefore ;
    endTime.after = endTimeAfter ;
  }else if (timeBeforeDis.stamp && timeBeforeDis.precision){
    var endTimeBefore = getTimeWithLangLabel(timeBeforeDis.stamp.value, timeBeforeDis.precision.value, lang) ;
    endTime.before = endTimeBefore ;
  }else if (timeAfterDis.stamp && timeAfterDis.precision){
    var endTimeAfter = getTimeWithLangLabel(timeAfterDis.stamp.value, timeAfterDis.precision.value, lang) ;
    endTime.after = endTimeAfter ;
  }

  return {"appTime":startTime, "disTime":endTime}
}


function createTimelineFeature(attrVersion, attrType, attrVersionValues, attrLabels = {}, timeME = {}, timeO = {}) {
  var groupName = attrLabels.get(attrType.value)?.label || attrType.value;
  var text = createTimelineText(attrVersion, attrVersionValues);

  var feature = {
    "group": groupName,
    "background": { "color": "#1c244b" },
    "unique_id": attrVersion.value
  };

  // --- Calcul de startTime (makesEffective) ---
  var startTime = undefined;
  if (timeME.crisp && timeME.crisp.stamp && timeME.crisp.precision) {
    // Cas Crisp : Temps net
    startTime = createTime(timeME.crisp.stamp.value, timeME.crisp.precision.value);
  } else if (timeME.fuzzy) {
    var beg = timeME.fuzzy.beginning;
    var end = timeME.fuzzy.end;

    if (beg && beg.stamp && end && end.stamp) {
      // Cas Fuzzy complet : On utilise les deux bornes
      startTime = createTimeFromTwoTimes(beg.stamp.value, beg.precision?.value, end.stamp.value, end.precision?.value);
    } else if (beg && beg.stamp) {
      // Cas Fuzzy partiel : Uniquement le début
      startTime = createTime(beg.stamp.value, beg.precision?.value);
    } else if (end && end.stamp) {
      // Cas Fuzzy partiel : Uniquement la fin
      startTime = createTime(end.stamp.value, end.precision?.value);
    }
  }

  // --- Calcul de endTime (outdates) ---
  var endTime = undefined;
  if (timeO.crisp && timeO.crisp.stamp && timeO.crisp.precision) {
    // Cas Crisp : Temps net
    endTime = createTime(timeO.crisp.stamp.value, timeO.crisp.precision.value);
  } else if (timeO.fuzzy) {
    var beg = timeO.fuzzy.beginning;
    var end = timeO.fuzzy.end;

    if (beg && beg.stamp && end && end.stamp) {
      // Cas Fuzzy complet
      endTime = createTimeFromTwoTimes(beg.stamp.value, beg.precision?.value, end.stamp.value, end.precision?.value);
    } else if (beg && beg.stamp) {
      endTime = createTime(beg.stamp.value, beg.precision?.value);
    } else if (end && end.stamp) {
      endTime = createTime(end.stamp.value, end.precision?.value);
    }
  }

  feature["start_date"] = startTime;
  feature["end_date"] = endTime;
  feature["text"] = text;

  return feature;
}

function createTimelineText(attrVersion, attrVersionValues){
  var values = [];
  attrVersionValues.forEach(element => {
    values.push(escapeHtml(element.value));
  });

  // 1. Label lisible (ex: "Nom_v1")
  var label = escapeHtml(attrVersion.value.split("/").pop());
  
  // 2. Formatage du headline en lien HTML cliquable vers l'URI de la version
  var headline = /^https?:\/\//.test(attrVersion.value)
    ? `<a href="${escapeHtml(attrVersion.value)}" target="_blank" rel="noopener noreferrer">${label}</a>`
    : label;

  var text = { 
    "headline": headline, 
    "text": values.join("<br>") 
  };

  return text;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]));
}

module.exports = { createTimelineFeature };


/**
 * Calcule la date médiane entre deux bornes ISO
 */
function getMidDate(dateStr1, dateStr2) {
  const d1 = dateStr1 ? new Date(dateStr1) : null;
  const d2 = dateStr2 ? new Date(dateStr2) : null;

  if (d1 && d2 && !isNaN(d1) && !isNaN(d2)) {
    const midTime = new Date((d1.getTime() + d2.getTime()) / 2);
    return parseSparqlDate(midTime.toISOString());
  }
  return parseSparqlDate(dateStr1 || dateStr2);
}

/**
 * Traite les bornes de début/fin (Crisp, Fuzzy, Infinis)
 */
function processVersionDates(version) {
  let startDate = null;
  let endDate = null;
  let isStartFuzzy = false;
  let isEndFuzzy = false;
  let isStartInfinite = false;
  let isEndInfinite = false;

  // --- 1. DÉBUT ---
  if (version.tStampME) {
    // Date précise
    startDate = parseSparqlDate(version.tStampME);
  } else if (version.tStampMEFuzzyBeg || version.tStampMEFuzzyEnd) {
    // Date floue -> Médiane entre le début et la fin de la fenêtre floue
    startDate = getMidDate(version.tStampMEFuzzyBeg, version.tStampMEFuzzyEnd);
    isStartFuzzy = true;
  } else {
    // Moins l'infini -> Année sentinelle pour le placement
    startDate = { year: -9999, month: 1, day: 1 };
    isStartInfinite = true;
  }

  // --- 2. FIN ---
  if (version.tStampO) {
    // Date précise
    endDate = parseSparqlDate(version.tStampO);
  } else if (version.tStampOFuzzyBeg || version.tStampOFuzzyEnd) {
    // Date floue
    endDate = getMidDate(version.tStampOFuzzyBeg, version.tStampOFuzzyEnd);
    isEndFuzzy = true;
  } else if (version.hasExplicitNoEnd) {
    // Si la donnée indique explicitement qu'il n'y a pas de fin (ou indéfinie)
    endDate = { year: 9999, month: 12, day: 31 };
    isEndInfinite = true;
  }

  return {
    startDate,
    endDate,
    isStartFuzzy,
    isEndFuzzy,
    isStartInfinite,
    isEndInfinite
  };
}

/**
 * Génère le libellé textuel pour la période
 */
function formatDisplayDate(dateInfo, dict) {
  const formatSingle = (d, isFuzzy, isInf) => {
    if (isInf) return "∞";
    if (!d || !d.year) return "?";
    const str = `${d.year}${d.month ? '-' + String(d.month).padStart(2, '0') : ''}`;
    return isFuzzy ? `~${str}` : str;
  };

  const startStr = formatSingle(dateInfo.startDate, dateInfo.isStartFuzzy, dateInfo.isStartInfinite);
  const endStr = formatSingle(dateInfo.endDate, dateInfo.isEndFuzzy, dateInfo.isEndInfinite);

  if (dateInfo.isStartInfinite && !dateInfo.endDate) {
    return `${dict.before || 'Jusqu\'à'} ${endStr}`;
  }
  if (!dateInfo.endDate || dateInfo.isEndInfinite) {
    return `${dict.since || 'Depuis'} ${startStr}`;
  }

  return `${startStr} ➔ ${endStr}`;
}


function parseSparqlDate(dateStr) {
  if (!dateStr) return null;

  // 1. Découpage manuel ISO (ex: "1163-03-24T00:00:00" ou "1862")
  const match = String(dateStr).match(/^^(-?\d+)(?:-(\d{2}))?(?:-(\d{2}))?/);
  if (match) {
    return {
      year: parseInt(match[1], 10),
      month: match[2] ? parseInt(match[2], 10) : 1,
      day: match[3] ? parseInt(match[3], 10) : 1
    };
  }

  // 2. Fallback avec Date standard
  const d = new Date(dateStr);
  if (!isNaN(d.getTime())) {
    return {
      year: d.getFullYear(),
      month: d.getMonth() + 1,
      day: d.getDate()
    };
  }

  return null;
}