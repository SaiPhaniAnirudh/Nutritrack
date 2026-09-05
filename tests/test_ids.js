const fs = require('fs');
const html = fs.readFileSync('frontend/index.html', 'utf8');

const ids = [
  'timeGreet', 'greetName', 'greetDate', 'navAvatar', 'navName',
  'editCalGoal', 'editProtGoal', 'editCarbGoal', 'editFatGoal',
  'editFiberGoal', 'editSugarGoal', 'editSodiumGoal', 'editCholGoal',
  'editVitDGoal', 'editIronGoal', 'editFolateGoal', 'quickAssistantBar',
  'dietWidgetTag', 'authSection', 'onboardingSection', 'mainApp'
];

ids.forEach(id => {
  const exists = html.includes(`id="${id}"`) || html.includes(`id='${id}'`);
  console.log(`${id}: ${exists ? 'EXISTS' : 'MISSING ❌'}`);
});
