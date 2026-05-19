//////////////////////////////// Variables //////////////////////////////////

const uiConfig = {

  avalaibleLanguages: ["fr", "en"],

  dateSlider: {
    min : 0,
    max : 100,
    value : 0
  },

  divIds: {
    content: "content",
    selection: "selection",

    radioInput: "radio-input",
    radioInputButtons: "radio-input-buttons",

    graph: "graph",
    graphSelection: "graph-selection",

    landmarkSelection: "landmark-selection",
    landmarkValidTime: "landmark-valid-time",

    landmarkTypeNames: "landmark-type-names",
    landmarkTypeNamesLabel: "landmark-type-names-label",

    landmarkNames: "landmark-names",
    landmarkNamesLabel: "landmark-names-label",

    landmarkSelectionSuggestions: "landmark-suggestions",

    landmarkValidationButton: "landmark-validation-button",

    mapTimeline: "map-timeline",
    timeline: "timeline",

    map: "leaflet-map",
    mapTimelineResizer: "map-timeline-resizer",

    dateSelection: "date-selection",
    dateSlider: "date-slider",
    dateInput: "date-input",
    dateValidationButton: "date-validation-button"
  },

  classNames: {
    resizer: "resizer"
  },

  labels : {
    snapshot: {
      fr: "Snapshot",
      en: "Snapshot"
    },
    validationButton: {
      fr: "Valider",
      en: "Validate"
    },
    dateSelection: {
      fr: "Sélectionnez une date : ",
      en: "Select a date:"
    },
    nameTitle: {
      fr: "Nom",
      en: "Name"
    },

    landmarkSelection: {
      fr: "Entité à sélectionner : ",
      en: "Entity to select:"
    },
    landmarkSelectValue: {
      fr: "Sélectionnez une entité",
      en: "Select an entity"
    },
    landmarkTypeSelectValue: {
      fr: "Sélectionnez un type d'entité",
      en: "Select an entity type"
    },
    searchLandmarksPlaceholder: {
      fr: "Rechercher un landmark...",
      en: "Search for a landmark..."
    },
    flyOverLandmark: {
      fr: "Survolez un lieu",
      en: "Hover over a location"
    },

    radioInput: {
      fr: "Type de visualisation",
      en: "Visualization type"
    },
    landmarkEvolution: {
      fr: "Évolution des repères",
      en: "Landmark evolution"
    },
    graphSelection: {
      fr: "Graphe à sélectionner : ",
      en: "Graph to select:"
    },
    graphSelectValue: {
      fr: "Sélectionnez un graphe",
      en: "Select a graph"
    },

    graphSelectionAlert: {
      fr: "Impossible de récupérer les graphes.",
      en: "Unable to retrieve graphs."
    },
    noLandmarkToDisplayAlert: {
      fr: "Aucun repère à afficher à cette date.",
      en: "No landmark to display at this date."
    }

  },

  systemLang : "en",

  dropDownMenu : {
    limit: 20,
  },

  map: {
    lat: 48.8566,
    lon: 2.3522,
    zoom: 13,

    style: {
        height:"90%",
        width:"100%",
    },

    tileLayers: [
      // { type:"xyz", url:"https://tile.openstreetmap.org/{z}/{x}/{y}.png", name:"OpenStreetMap" },
      { type:"xyz", url:"https://tile.openstreetmap.de/{z}/{x}/{y}.png ", name:"OpenStreetMap" },
      { type:"wms", url:"https://geohistoricaldata.org/geoserver/paris-rasters/wms", layer:"paris-rasters:verniquet_1789", name:"Atlas de Verniquet (1789)" },
      { type:"wms", url:"https://geohistoricaldata.org/geoserver/paris-rasters/wms", layer:"paris-rasters:jacoubet_1836", name:"Plan de Jacoubet (1836)" },
      { type:"wms", url:"https://geohistoricaldata.org/geoserver/paris-rasters/wms", layer:"paris-rasters:andriveau_1849", name:"Plan d'Andriveau (1849)" },
      { type:"wms", url:"https://geohistoricaldata.org/geoserver/paris-rasters/wms", layer:"paris-rasters:poubelle_1888", name:"Plan Poubelle (1888)" },
      { type:"xyz", url:"https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png", name:"OpenStreetMap Hot" }
    ]
  },

  radioInputs :{
    values : {
      snapshot: {
        label: {
          fr: "Snapshot",
          en: "Snapshot"
        },
        id: "snapshot-selection"
      },
      timeline: {
        label: {
          fr: "Évolution des repères",
          en: "Landmark evolution"
        },
        id: "timeline-selection"
      }
    },

    style: {
      display: "flex",
      flexDirection: "row",
    }
  },

  timeline: {
    startTimestamp: "1790-01-01",
    endTimestamp: "2027-01-01",
    timeDelay: 20, // years (null = no delay),
    headlineLabel: {
      fr: "Attributs de l'entité géographique",
      en: "Attributes of the geographic entity"
    }
  },

  calendar: {
    uri: gregorianCalendarURI
  },

  layers: {
    certain: {
      fr: "Certains",
      en: "Certain"
    },
    uncertain: {
      fr: "Incertains",
      en: "Uncertain"
    }
  },

  types: {
    attributes: null, // to be filled with the result of the query getQueryForAttributeTypes
    landmarks: null, // to be filled with the result of the query getQueryForLandmarkTypes
  }
};

function setSystemLang(uiConfig, lang) {
  if (!uiConfig.avalaibleLanguages.includes(lang)){
    console.warn(`Language ${lang} not available in the UI configuration. Falling back to default language ${uiConfig.avalaibleLanguages[0]}.`);
    lang = uiConfig.avalaibleLanguages[0];
  }
  uiConfig.lang = lang;
}

function setGraphLang(uiConfig, lang) {
  if (!uiConfig.avalaibleLanguages.includes(lang)){
    console.warn(`Language ${lang} not available in the UI configuration. Falling back to default language ${uiConfig.avalaibleLanguages[0]}.`);
    lang = uiConfig.avalaibleLanguages[0];
  }
  uiConfig.graphLang = lang;
}