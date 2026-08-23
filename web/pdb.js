/* KEYHOLE fixed-column legacy PDB parser. */
(function (global) {
  "use strict";

  var MAX_TEXT = 25000000;
  var MAX_ATOMS = 250000;
  var RADII = { H: 0.31, C: 0.76, N: 0.71, O: 0.66, S: 1.05, P: 1.07, HG: 1.32 };

  function field(line, start, end) {
    return line.length > start ? line.slice(start, end).trim() : "";
  }

  function numberField(line, start, end, fallback) {
    var value = Number(field(line, start, end));
    return Number.isFinite(value) ? value : fallback;
  }

  function elementFor(atomName, supplied) {
    if (supplied) { return supplied.toUpperCase(); }
    var letters = atomName.replace(/[^A-Za-z]/g, "").toUpperCase();
    if (!letters) { return "C"; }
    if (letters.slice(0, 2) === "HG") { return "HG"; }
    return letters.charAt(0);
  }

  function siteKey(atom) {
    return [atom.record, atom.chain, atom.resSeq, atom.iCode, atom.resName, atom.name].join("|");
  }

  function chooseConformers(rawAtoms) {
    var groups = new Map();
    rawAtoms.forEach(function (atom) {
      var key = siteKey(atom);
      if (!groups.has(key)) { groups.set(key, []); }
      groups.get(key).push(atom);
    });
    var selected = [];
    groups.forEach(function (alternatives) {
      var blanks = alternatives.filter(function (atom) { return atom.altLoc === ""; });
      var choices = blanks.length ? blanks : alternatives;
      choices.sort(function (left, right) {
        return right.occupancy - left.occupancy || left.altLoc.localeCompare(right.altLoc);
      });
      selected.push(choices[0]);
    });
    selected.sort(function (left, right) { return left.serial - right.serial; });
    return selected;
  }

  function distance(left, right) {
    var dx = left.x - right.x;
    var dy = left.y - right.y;
    var dz = left.z - right.z;
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
  }

  function bondKey(left, right) {
    return left < right ? left + ":" + right : right + ":" + left;
  }

  function inferBonds(atoms, explicitPairs) {
    var atomBySerial = new Map();
    atoms.forEach(function (atom) { atomBySerial.set(atom.serial, atom); });
    var bonds = new Map();
    (explicitPairs || []).forEach(function (pair) {
      if (atomBySerial.has(pair[0]) && atomBySerial.has(pair[1]) && pair[0] !== pair[1]) {
        bonds.set(bondKey(pair[0], pair[1]), { from: pair[0], to: pair[1], explicit: true });
      }
    });

    var residues = new Map();
    atoms.forEach(function (atom) {
      if (atom.record !== "ATOM" || atom.resName === "HOH" || atom.resName === "WAT") { return; }
      var key = [atom.chain, atom.segment, atom.resSeq, atom.iCode, atom.resName].join("|");
      if (!residues.has(key)) { residues.set(key, []); }
      residues.get(key).push(atom);
    });
    residues.forEach(function (residueAtoms) {
      for (var i = 0; i < residueAtoms.length; i += 1) {
        for (var j = i + 1; j < residueAtoms.length; j += 1) {
          var left = residueAtoms[i];
          var right = residueAtoms[j];
          var threshold = (RADII[left.element] || 0.77) + (RADII[right.element] || 0.77) + 0.45;
          var separation = distance(left, right);
          if (separation > 0.4 && separation <= threshold) {
            bonds.set(bondKey(left.serial, right.serial), {
              from: left.serial, to: right.serial, explicit: false
            });
          }
        }
      }
    });

    var chains = new Map();
    residues.forEach(function (residueAtoms) {
      var first = residueAtoms[0];
      var key = first.chain + "|" + first.segment;
      if (!chains.has(key)) { chains.set(key, []); }
      chains.get(key).push(residueAtoms);
    });
    chains.forEach(function (chainResidues) {
      chainResidues.sort(function (left, right) {
        return left[0].serial - right[0].serial;
      });
      for (var index = 1; index < chainResidues.length; index += 1) {
        var previousC = chainResidues[index - 1].find(function (atom) { return atom.name === "C"; });
        var nextN = chainResidues[index].find(function (atom) { return atom.name === "N"; });
        if (previousC && nextN && distance(previousC, nextN) <= 1.8) {
          bonds.set(bondKey(previousC.serial, nextN.serial), {
            from: previousC.serial, to: nextN.serial, explicit: false
          });
        }
      }
    });
    return Array.from(bonds.values()).sort(function (left, right) {
      return left.from - right.from || left.to - right.to;
    });
  }

  function parse(text) {
    if (typeof text !== "string" || text.length === 0 || text.length > MAX_TEXT) {
      throw new Error("PDB text must be a non-empty bounded string");
    }
    var lines = text.replace(/\r/g, "").split("\n");
    var rawAtoms = [];
    var explicitPairs = [];
    var titleParts = [];
    var method = "";
    var resolution = null;
    var headerId = "";
    var segment = 0;
    var modelSeen = false;
    var acceptingModel = true;
    var firstModelFinished = false;

    lines.forEach(function (line) {
      var record = field(line, 0, 6);
      if (record === "MODEL") {
        if (!modelSeen) {
          modelSeen = true;
          acceptingModel = true;
        } else {
          acceptingModel = false;
        }
        return;
      }
      if (record === "ENDMDL") {
        if (acceptingModel) { firstModelFinished = true; }
        acceptingModel = false;
        return;
      }
      if (record === "HEADER") { headerId = field(line, 62, 66); }
      if (record === "TITLE") { titleParts.push(field(line, 10, 80)); }
      if (record === "EXPDTA") { method = field(line, 10, 80); }
      if (record === "REMARK" && field(line, 7, 10) === "2" && line.indexOf("RESOLUTION.") >= 0) {
        var match = line.match(/RESOLUTION\.\s+([0-9.]+)\s+ANGSTROMS/);
        if (match) { resolution = Number(match[1]); }
      }
      if (record === "TER") { segment += 1; return; }
      if (record === "CONECT") {
        var serials = [];
        for (var offset = 6; offset < line.length; offset += 5) {
          var serial = Number(field(line, offset, offset + 5));
          if (Number.isInteger(serial)) { serials.push(serial); }
        }
        for (var connected = 1; connected < serials.length; connected += 1) {
          explicitPairs.push([serials[0], serials[connected]]);
        }
        return;
      }
      if ((record !== "ATOM" && record !== "HETATM") || !acceptingModel || firstModelFinished) {
        return;
      }
      if (rawAtoms.length >= MAX_ATOMS) { throw new Error("PDB atom limit exceeded"); }
      var x = numberField(line, 30, 38, NaN);
      var y = numberField(line, 38, 46, NaN);
      var z = numberField(line, 46, 54, NaN);
      if (![x, y, z].every(Number.isFinite)) { return; }
      var name = field(line, 12, 16);
      var resName = field(line, 17, 20);
      rawAtoms.push({
        record: record,
        serial: numberField(line, 6, 11, rawAtoms.length + 1),
        name: name,
        altLoc: field(line, 16, 17),
        resName: resName,
        chain: field(line, 21, 22) || "_",
        resSeq: numberField(line, 22, 26, 0),
        iCode: field(line, 26, 27),
        x: x, y: y, z: z,
        occupancy: numberField(line, 54, 60, 1),
        bFactor: numberField(line, 60, 66, 0),
        element: elementFor(name, field(line, 76, 78)),
        charge: field(line, 78, 80),
        segment: segment,
        water: resName === "HOH" || resName === "WAT"
      });
    });

    var atoms = chooseConformers(rawAtoms);
    var residues = new Map();
    var chains = new Map();
    atoms.forEach(function (atom) {
      var residueKey = [atom.chain, atom.segment, atom.resSeq, atom.iCode, atom.resName].join("|");
      if (!residues.has(residueKey)) {
        residues.set(residueKey, {
          chain: atom.chain, segment: atom.segment, resSeq: atom.resSeq,
          iCode: atom.iCode, resName: atom.resName, record: atom.record
        });
      }
      chains.set(atom.chain, (chains.get(atom.chain) || 0) + 1);
    });
    return {
      metadata: {
        pdbId: headerId,
        title: titleParts.join(" ").replace(/\s+/g, " ").trim(),
        method: method,
        resolutionAngstrom: resolution
      },
      rawAtoms: rawAtoms,
      atoms: atoms,
      residues: Array.from(residues.values()),
      chains: Object.fromEntries(chains),
      bonds: inferBonds(atoms, explicitPairs),
      stats: {
        rawCoordinateRecords: rawAtoms.length,
        selectedAtomSites: atoms.length,
        alternateRecords: rawAtoms.filter(function (atom) { return atom.altLoc !== ""; }).length,
        zeroOccupancyRecords: rawAtoms.filter(function (atom) { return atom.occupancy === 0; }).length,
        waterAtomSites: atoms.filter(function (atom) { return atom.water; }).length,
        heteroAtomSites: atoms.filter(function (atom) { return atom.record === "HETATM"; }).length
      }
    };
  }

  global.KEYHOLE = global.KEYHOLE || {};
  global.KEYHOLE.pdb = Object.freeze({
    chooseConformers: chooseConformers,
    inferBonds: inferBonds,
    parse: parse
  });
})(window);
