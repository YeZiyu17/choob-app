"""Exercise the real Passport submit handler against pre-Snap meal records."""

from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("node"), "Node is needed to execute the Passport editor")
class PassportEditTests(unittest.TestCase):
    def test_address_edit_preserves_legacy_meal_status_and_other_dishes(self):
        result = subprocess.run(
            [shutil.which("node"), "--input-type=commonjs", "-e", _EDITOR_HARNESS],
            input=(ROOT / "index.html").read_text(encoding="utf-8"),
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Passport legacy edit passed", result.stdout)


_EDITOR_HARNESS = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const html = require('node:fs').readFileSync(0, 'utf8');

// Execute the application's functions and registered submit handler, not a
// second implementation of saving or classifying meal records.
const locationAndStatus = html.slice(
  html.indexOf('  function hasMealLocation(item)'),
  html.indexOf('  function trySource(item)')
);
const identity = html.slice(
  html.indexOf('  function findSavedMealIndex(list,item)'),
  html.indexOf('  function mealTitle(item,')
);
const start = html.indexOf("passportEditForm.addEventListener('submit',event=>{");
const end = html.indexOf('\nfunction deleteSavedMeal(item)', start);
assert.ok(start > 0 && end > start, 'Passport submit handler must be present');

function exercise({changeAddress = true, storageWorks = true} = {}) {
  const legacy = {
    dish_name:'Sushi', restaurant_name:'Kaze', address:'10 Old Street',
    saved_at:'2026-11-01T12:00:00Z', image:'data:image/jpeg;base64,fixture',
    location:{lat:39.95,lng:-75.16,label:'Kaze'},
    dishes:[
      {dish_name:'Sushi',cuisine:'Japanese',category:'Seafood',rating:5,note:'Fresh'},
      {dish_name:'Gyoza',cuisine:'Japanese',category:'Dumpling',rating:2,note:'Too salty'}
    ]
  };
  const original = JSON.stringify(legacy);
  const values = {
    mealEditName:'Dinner with friends', mealEditEmoji:'🍣',
    mealEditRestaurant:'New Kaze',
    mealEditAddress:changeAddress?'20 New Street':'10 Old Street',
    mealEditCuisine:'Japanese', mealEditCategory:'Seafood',
    mealEditRating:'4', mealEditNote:'Updated note', mealEditError:''
  };
  const fields = Object.fromEntries(Object.entries(values).map(([id,value])=>[id,{value,textContent:''}]));
  let submit, persisted, closed = false;
  const context = {
    editingMeal:legacy,
    passportEditForm:{addEventListener(type, handler) { assert.equal(type,'submit'); submit=handler; }},
    getSaved:()=>[JSON.parse(original)],
    mealEditInput:id=>fields[id],
    badgeForMeal:()=> '🍽️',
    persistSaved:list=>{
      if (!storageWorks) return false;
      persisted=JSON.parse(JSON.stringify(list));
      return true;
    },
    mealEditDialog:{close() { closed=true; }},
    renderSaved() {}, currentScreen:'collectionScreen', renderPassportMap() {},
    openSavedMeal() {}, showToast() {}
  };
  vm.createContext(context);
  vm.runInContext(locationAndStatus + identity + html.slice(start,end), context);
  assert.equal(context.isWantToTry(legacy),false,'a located historical record is a logged meal');
  submit({preventDefault() {}});
  assert.equal(JSON.stringify(legacy),original,'editing must not mutate the input record');
  if (!storageWorks) {
    assert.equal(persisted,undefined);
    assert.equal(closed,false);
    assert.match(fields.mealEditError.textContent,/Could not save/);
    return;
  }
  const meal = persisted[0];
  assert.equal(context.isWantToTry(meal),false,'editing an address must not move a logged meal to Saved dishes');
  assert.equal(meal.want_to_try,false);
  assert.equal(meal.source,undefined,'do not invent a Snap origin for legacy records');
  assert.equal(meal.display_name,'Dinner with friends');
  assert.equal(meal.dishes[0].rating,4);
  assert.equal(meal.dishes[0].note,'Updated note');
  assert.deepEqual(meal.dishes[1],legacy.dishes[1],'other dishes retain their ratings and notes');
  assert.equal(meal.image,legacy.image);
  assert.equal(meal.saved_at,legacy.saved_at);
  assert.equal(closed,true);
  if (changeAddress) assert.equal(meal.location,undefined,'the old coordinates no longer describe the edited address');
  else assert.deepEqual(meal.location,{lat:39.95,lng:-75.16,label:'New Kaze'});
  assert.equal(context.isWantToTry({restaurant_name:'Kaze'}),true,'old unlogged restaurant saves remain ideas');
  assert.equal(context.isWantToTry({restaurant_name:'Kaze',want_to_try:false}),false);
  assert.equal(context.isWantToTry({restaurant_name:'Kaze',want_to_try:true,location:legacy.location}),true);
}

exercise();
exercise({changeAddress:false});
exercise({storageWorks:false});
console.log('Passport legacy edit passed');
"""


if __name__ == "__main__":
    unittest.main()
