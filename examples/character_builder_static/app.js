const abilityNames = {
  str: "Strength",
  dex: "Dexterity",
  con: "Constitution",
  int: "Intelligence",
  wis: "Wisdom",
  cha: "Charisma",
};

const state = {
  options: null,
  summary: null,
};

const $ = (id) => document.getElementById(id);

function title(value) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function signed(value) {
  return value >= 0 ? `+${value}` : `${value}`;
}

async function init() {
  state.options = await fetch("/api/options").then((response) => response.json());
  fillSelect($("class"), state.options.classes, "name", "name");
  fillSelect($("race"), state.options.races, "id", "name");
  fillSelect($("armor"), [{ id: "", name: "None" }, ...state.options.armor], "id", "name");
  fillSelect($("shield"), [{ id: "", name: "None" }, ...state.options.shields], "id", "name");
  $("class").value = "fighter";
  $("race").value = "human";
  renderAbilities();
  renderSubraces();
  renderSkills();
  renderWeapons();
  bindInputs();
  await refresh();
}

function fillSelect(select, rows, valueKey, labelKey) {
  select.innerHTML = rows
    .map((row) => `<option value="${row[valueKey]}">${title(String(row[labelKey]))}</option>`)
    .join("");
}

function renderAbilities() {
  $("abilities").innerHTML = state.options.abilities
    .map(
      (ability) => `
        <label class="ability-card">
          <span>${abilityNames[ability]}</span>
          <strong id="${ability}Bonus">+0</strong>
          <input id="${ability}" type="number" min="1" max="30" value="10" />
        </label>
      `,
    )
    .join("");
  $("str").value = 16;
  $("dex").value = 14;
  $("con").value = 14;
  $("wis").value = 12;
  $("cha").value = 8;
}

function renderSubraces() {
  const race = currentRace();
  const rows = [{ id: "", name: "None" }, ...state.options.subraces.filter((row) => row.race_id === race.id)];
  fillSelect($("subrace"), rows, "id", "name");
  const abilityChoices = $("abilityChoices");
  const languageChoices = $("languageChoices");
  abilityChoices.innerHTML = "";
  languageChoices.innerHTML = "";
  if (race.ability_bonus_choice_count > 0) {
    abilityChoices.innerHTML = state.options.abilities
      .map(
        (ability) => `
          <label class="check">
            <input type="checkbox" name="abilityChoice" value="${ability}" />
            ${abilityNames[ability]}
          </label>
        `,
      )
      .join("");
    [...abilityChoices.querySelectorAll("input")]
      .slice(0, race.ability_bonus_choice_count)
      .forEach((input) => {
        input.checked = true;
      });
  }
  if (race.language_choice_count > 0) {
    languageChoices.innerHTML = race.language_options
      .map(
        (language) => `
          <label class="check">
            <input type="checkbox" name="languageChoice" value="${language}" />
            ${title(language)}
          </label>
        `,
      )
      .join("");
    [...languageChoices.querySelectorAll("input")]
      .slice(0, race.language_choice_count)
      .forEach((input) => {
        input.checked = true;
      });
  }
}

function renderSkills() {
  const classDefinition = currentClass();
  $("skillHint").textContent = `Choose ${classDefinition.skill_choice_count}`;
  $("skills").innerHTML = classDefinition.skill_choices
    .map(
      (skill) => `
        <label class="check">
          <input type="checkbox" name="skill" value="${skill}" />
          ${title(skill)}
        </label>
      `,
    )
    .join("");
  const picks = classDefinition.skill_choices.slice(0, classDefinition.skill_choice_count);
  document.querySelectorAll("input[name='skill']").forEach((input) => {
    input.checked = picks.includes(input.value);
  });
}

function renderWeapons() {
  $("weapons").innerHTML = state.options.weapons
    .map(
      (weapon) => `
        <label class="check">
          <input type="checkbox" name="weapon" value="${weapon.id}" />
          <span>${weapon.name} <small>${weapon.damage_dice} ${weapon.damage_type}</small></span>
        </label>
      `,
    )
    .join("");
  ["longsword", "shortbow"].forEach((id) => {
    const input = document.querySelector(`input[name='weapon'][value='${id}']`);
    if (input) input.checked = true;
  });
  $("armor").value = "chain_mail";
  $("shield").value = "shield";
}

function bindInputs() {
  document.body.addEventListener("input", refresh);
  document.body.addEventListener("change", (event) => {
    if (event.target.id === "race") renderSubraces();
    if (event.target.id === "class") renderSkills();
    refresh();
  });
  $("standardArray").addEventListener("click", () => {
    const scores = { str: 15, dex: 14, con: 13, int: 10, wis: 12, cha: 8 };
    Object.entries(scores).forEach(([ability, score]) => {
      $(ability).value = score;
    });
    refresh();
  });
  $("downloadJson").addEventListener("click", downloadJson);
}

async function refresh() {
  const error = $("error");
  error.textContent = "";
  try {
    const response = await fetch("/api/character", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload()),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to build character");
    state.summary = data;
    renderSummary(data);
  } catch (err) {
    error.textContent = err.message;
  }
}

function payload() {
  const abilities = {};
  state.options.abilities.forEach((ability) => {
    abilities[ability] = Number($(ability).value || 10);
  });
  return {
    name: $("name").value,
    class: $("class").value,
    level: Number($("level").value || 1),
    race: $("race").value,
    subrace: $("subrace").value,
    abilityChoices: checkedValues("abilityChoice"),
    languageChoices: checkedValues("languageChoice"),
    skills: checkedValues("skill"),
    abilities,
    armor: $("armor").value,
    shield: $("shield").value,
    weapons: checkedValues("weapon"),
    twoHandedWeapons: checkedValues("weapon").filter((id) => {
      const weapon = state.options.weapons.find((item) => item.id === id);
      return weapon && weapon.properties.includes("versatile");
    }),
    maximumHitPoints: $("maximumHitPoints").value,
    currentHitPoints: $("currentHitPoints").value,
  };
}

function checkedValues(name) {
  return [...document.querySelectorAll(`input[name='${name}']:checked`)].map((input) => input.value);
}

function currentClass() {
  return state.options.classes.find((row) => row.name === $("class").value);
}

function currentRace() {
  return state.options.races.find((row) => row.id === $("race").value);
}

function renderSummary(data) {
  const sheet = data.sheet;
  $("summaryName").textContent = sheet.name;
  $("summaryLine").textContent = `${title(data.lineage.race.name)} ${title(sheet.classes[0].name)} ${sheet.classes[0].level}`;
  $("armorClass").textContent = data.derived.armorClass.total;
  $("hitPoints").textContent = `${data.derived.hitPoints.current}/${data.derived.hitPoints.maximum}`;
  $("initiative").textContent = signed(data.derived.initiative);
  $("proficiency").textContent = signed(data.derived.proficiencyBonus);

  data.abilities.forEach((ability) => {
    const bonus = $(ability.id + "Bonus");
    if (bonus) bonus.textContent = `${signed(ability.modifier)} (${ability.score})`;
  });

  $("abilitySummary").innerHTML = data.abilities
    .map(
      (ability) => `
        <div class="mini">
          <span>${ability.name}</span>
          <strong>${ability.score}</strong>
          <small>${signed(ability.modifier)} mod</small>
        </div>
      `,
    )
    .join("");

  $("attacks").innerHTML =
    data.derived.attacks
      .map(
        (attack) => `
          <div class="row">
            <div>
              <strong>${attack.weapon.name}</strong>
              <small>${attack.damage_dice} ${signed(attack.damage_bonus)} ${attack.damage_type}</small>
            </div>
            <strong>${signed(attack.attack_bonus)}</strong>
          </div>
        `,
      )
      .join("") || `<div class="row"><span>No equipped weapons</span></div>`;

  $("features").innerHTML =
    data.derived.progression.features
      .map(
        (feature) => `
          <div class="row">
            <div>
              <strong>${feature.name}</strong>
              <small>${feature.level ? `level ${feature.level}` : title(feature.source_type)}</small>
            </div>
            <small>${title(feature.class_id || feature.source_type)}</small>
          </div>
        `,
      )
      .join("") || `<div class="row"><span>No class features</span></div>`;

  $("spellcasting").innerHTML = renderSpellcasting(data.derived.spellcasting);

  $("saves").innerHTML = data.derived.savingThrows
    .map(
      (save) => `
        <div class="mini">
          <span>${save.name}${save.proficient ? " *" : ""}</span>
          <strong>${signed(save.bonus)}</strong>
        </div>
      `,
    )
    .join("");

  $("skillSummary").innerHTML = data.derived.skills
    .map(
      (skill) => `
        <div class="row">
          <div><strong>${skill.name}${skill.proficient ? " *" : ""}</strong> <small>${skill.ability}</small></div>
          <strong>${signed(skill.bonus)}</strong>
        </div>
      `,
    )
    .join("");

  const traits = data.lineage.traits.length ? data.lineage.traits.map(title).join(", ") : "No listed traits";
  $("lineage").textContent = `${data.lineage.languages.map(title).join(", ")}. ${traits}.`;
}

function downloadJson() {
  if (!state.summary) return;
  const blob = new Blob([JSON.stringify(state.summary.sheet, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${state.summary.sheet.id}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

function renderSpellcasting(spellcasting) {
  if (!spellcasting) return `<div class="row"><span>No class spellcasting table</span></div>`;
  const rows = [];
  if (spellcasting.cantrips_known !== null) {
    rows.push(`<div class="row"><span>Cantrips Known</span><strong>${spellcasting.cantrips_known}</strong></div>`);
  }
  if (spellcasting.spells_known !== null) {
    rows.push(`<div class="row"><span>Spells Known</span><strong>${spellcasting.spells_known}</strong></div>`);
  }
  Object.entries(spellcasting.spell_slots).forEach(([level, count]) => {
    rows.push(`<div class="row"><span>Level ${level} Slots</span><strong>${count}</strong></div>`);
  });
  return rows.join("") || `<div class="row"><span>No spell slots at this level</span></div>`;
}

init();
