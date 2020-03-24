document.addEventListener('DOMContentLoaded', function() {

    // open test result
    var testListEntries = document.getElementsByClassName("test-list-entry-default");
    let testContents = document.getElementsByClassName("single-test-content");
    for (var i = 0; i < testListEntries.length; i++) {
        testListEntries[i].addEventListener("click", function() {
            document.getElementById("single-test-placeholder").classList.add("hidden");
            for (var j = 0; j < testContents.length; j++) {
                testContents[j].classList.add("hidden");
            }
            for (var j = 0; j < testContents.length; j++) {
                var testContentsScenarioID = testContents[j].id.replace("scenario-", "")
                if (testContentsScenarioID == this.id.replace("entry-flat-", "")) {
                    testContents[j].classList.remove("hidden");
                    set_hash(testContentsScenarioID);
                    break;
                } else if (testContentsScenarioID == this.id.replace("entry-outline-", "")) {
                    testContents[j].classList.remove("hidden");
                    set_hash(testContentsScenarioID);
                    break;
                } else if (testContentsScenarioID == this.id.replace("entry-features-", "")) {
                    testContents[j].classList.remove("hidden");
                    set_hash(testContentsScenarioID);
                    break;
                } else if (testContentsScenarioID == this.id.replace("entry-exceptions-", "")) {
                    testContents[j].classList.remove("hidden");
                    set_hash(testContentsScenarioID);
                    break;
                }
            }
        });
    }

    let features = document.getElementsByClassName("feature")

    // open collapsible
    var coll = document.getElementsByClassName("collapsible");
    for (var i = 0; i < coll.length; i++) {
        coll[i].addEventListener("click", function() {
            this.classList.toggle("active");
            var content = this.nextElementSibling;
            content.classList.toggle("hidden")
        });
    }

    // open step attachment
    var coll = document.getElementsByClassName("step-attachment");
    for (var i = 0; i < coll.length; i++) {
        coll[i].addEventListener("click", function() {
            document.getElementById("file-modal").classList.remove("hidden");
            var folder = this.getElementsByClassName("step-attachment-folder")[0].innerHTML;
            var filename = this.getElementsByClassName("step-attachment-filename")[0].innerHTML;
            var type = this.getElementsByClassName("step-attachment-type")[0].innerHTML;
            document.getElementById("file-modal-filename").innerHTML = filename;
            document.getElementById("file-modal-type").innerHTML = type;
            document.getElementById("file-modal-description").innerHTML = this.getElementsByClassName("step-attachment-description")[0].innerHTML;

            if (type == 'plaintext') {
                Promise.all([
                    fetch(`${folder}/${filename}`).then(x => x.text())
                ]).then(([response]) => {
                    document.getElementById("file-modal-file-contents").innerHTML = `<div id="file-modal-contents-plaintext">${response}</div>`;
                });
            } else if (type == 'image') {
                Promise.all([
                    fetch(`${folder}/${filename}`).then(x => x.blob())
                ]).then(([blob]) => {
                    document.getElementById("file-modal-file-contents").innerHTML = `<img id="file-modal-contents-image" src="${URL.createObjectURL(blob)}">`;
                });
            }

            document.getElementById("file-modal-download").innerHTML = `<a href="${folder}/${filename}" download="${filename}">💾</a>`

        });
    }

    // show scenario log
    var coll = document.getElementsByClassName("show-log");
    for (var i = 0; i < coll.length; i++) {
        coll[i].addEventListener("click", function() {
            document.getElementById("file-modal").classList.remove("hidden");
            var folder = this.id.replace("show-log-", "");
            var filename = "scenario.log";
            var type = "plaintext";
            document.getElementById("file-modal-filename").innerHTML = filename;
            document.getElementById("file-modal-type").innerHTML = type;
            document.getElementById("file-modal-description").innerHTML = "Scenario log.";

            Promise.all([
                fetch(`${folder}/${filename}`).then(x => x.text())
            ]).then(([response]) => {
                document.getElementById("file-modal-file-contents").innerHTML = `<div id="file-modal-contents-plaintext">${response}</div>`;
            });
            document.getElementById("file-modal-download").innerHTML = `<a href="${folder}/${filename}" download="${filename}">💾</a>`
        });
    }

    // show test repeats
    var coll = document.getElementsByClassName("show-repeats");
    for (var i = 0; i < coll.length; i++) {
        coll[i].addEventListener("click", function() {
            var lastRepeatId = this.id.replace("show-repeats-", "").split("-")[0]
            var scenarioId = this.id.replace("show-repeats-", "").split("-")[1]
            document.getElementById(`scenario-${scenarioId}`).classList.add("hidden")
            document.getElementById(`scenario-repeat-list-${lastRepeatId}`).classList.remove("hidden")
        });
    }

    // open repeat
    var coll = document.getElementsByClassName("test-repeat-button");
    for (var i = 0; i < coll.length; i++) {
        coll[i].addEventListener("click", function() {
            var lastRepeatId = this.id.replace("test-repeat-button-", "").split("-")[0]
            var scenarioId = this.id.replace("test-repeat-button-", "").split("-")[1]
            document.getElementById(`scenario-${scenarioId}`).classList.remove("hidden")
            document.getElementById(`scenario-repeat-list-${lastRepeatId}`).classList.add("hidden")
            set_hash(scenarioId);
        });
    }

    // close file modal
    document.getElementById("file-modal-close").onclick = function() {
        document.getElementById("file-modal").classList.add("hidden");
    }


    // expand all steps
    var elems = document.getElementsByClassName("single-test-content");
    for (var i = 0; i < elems.length; i++) {
        var scenarioId = elems[i].id.split("-").slice(-1).pop()
        var buttonId = `toggle-steps-${scenarioId}`
        var scenarioStepClass = `scenario-${scenarioId}`
        var button = document.getElementById(buttonId)
        let scenarioSteps = document.getElementsByClassName(scenarioStepClass)

        button.addEventListener("click", function() {
            console.log("main click");
            if (button.classList.contains("off")) {
                for (var j = 0; j < scenarioSteps.length; j++) {
                    if (!scenarioSteps[j].classList.contains("active")) {
                        scenarioSteps[j].click()
                    }
                }
                console.log("expanding");
                button.classList.remove("off")
                button.innerHTML = "Collapse all";
                return;
            } else {
                for (var j = 0; j < scenarioSteps.length; j++) {
                    if (scenarioSteps[j].classList.contains("active")) {
                        scenarioSteps[j].click()
                    }
                }
                console.log("collapsing");
                button.classList.add("off")
                button.innerHTML = "Expand all";
                return;
            }
        });
    }

    // test list toolbar

    // TODO use radio buttons here

    let showFlatButton = document.getElementById("show-flat")
    let showOutlinesButton = document.getElementById("show-outlines")
    let showFeaturesButton = document.getElementById("show-features")
    let showExceptionsButton = document.getElementById("show-exceptions")

    let flatList = document.getElementById("test-list-flat")
    let outlinesList = document.getElementById("test-list-outlines")
    let featuresList = document.getElementById("test-list-features")
    let exceptionsList = document.getElementById("test-list-exceptions")

    showFlatButton.onclick = function() {
        showFlatButton.classList.add("selected");
        showOutlinesButton.classList.remove("selected");
        showFeaturesButton.classList.remove("selected");
        showExceptionsButton.classList.remove("selected");

        flatList.classList.remove("hidden");
        outlinesList.classList.add("hidden");
        featuresList.classList.add("hidden");
        exceptionsList.classList.add("hidden");
    }
    showOutlinesButton.onclick = function() {
        showFlatButton.classList.remove("selected");
        showOutlinesButton.classList.add("selected");
        showFeaturesButton.classList.remove("selected");
        showExceptionsButton.classList.remove("selected");

        flatList.classList.add("hidden");
        outlinesList.classList.remove("hidden");
        featuresList.classList.add("hidden");
        exceptionsList.classList.add("hidden");
    }
    showFeaturesButton.onclick = function() {
        showFlatButton.classList.remove("selected");
        showOutlinesButton.classList.remove("selected");
        showFeaturesButton.classList.add("selected");
        showExceptionsButton.classList.remove("selected");

        flatList.classList.add("hidden");
        outlinesList.classList.add("hidden");
        featuresList.classList.remove("hidden");
        exceptionsList.classList.add("hidden");
    }
    showExceptionsButton.onclick = function() {
        showFlatButton.classList.remove("selected");
        showOutlinesButton.classList.remove("selected");
        showFeaturesButton.classList.remove("selected");
        showExceptionsButton.classList.add("selected");

        flatList.classList.add("hidden");
        outlinesList.classList.add("hidden");
        featuresList.classList.add("hidden");
        exceptionsList.classList.remove("hidden");
    }

    // hider buttons
    let togglePassedButton = document.getElementById("toggle-passed")
    let toggleFailedButton = document.getElementById("toggle-failed")
    let toggleSkippedButton = document.getElementById("toggle-skipped")

    let passedEntries = document.getElementsByClassName("test-list-entry-passed");
    let failedEntries = document.getElementsByClassName("test-list-entry-failed");
    let skippedEntries = document.getElementsByClassName("test-list-entry-skipped");

    let passedCollapsibles = document.getElementsByClassName("collapsible-passed");
    let failedCollapsibles = document.getElementsByClassName("collapsible-failed");
    let skippedCollapsibles = document.getElementsByClassName("collapsible-skipped");

    let scenarioOutlines = document.getElementsByClassName("scenario-outline")

    let hiderButtons = [togglePassedButton, toggleFailedButton, toggleSkippedButton]
    let hiderButtonsKeys = ['passed', 'failed', 'skipped']
    let hiderEntries = [passedEntries, failedEntries, skippedEntries]
    let hiderCollapsibles = [passedCollapsibles, failedCollapsibles, skippedCollapsibles]

    for (let i = 0; i < hiderButtons.length; i++) {
        hiderButtons[i].onclick = function() {
            if (hiderButtons[i].classList.contains("off")) {
                for (var j = 0; j < hiderEntries[i].length; j++) {
                    hiderEntries[i][j].classList.remove("hidden");
                }
                for (var j = 0; j < hiderCollapsibles[i].length; j++) {
                    hiderCollapsibles[i][j].classList.remove("hidden");
                    hiderCollapsibles[i][j].classList.remove("active");
                }
                hiderButtons[i].classList.remove("off");
                hiderButtons[i].innerHTML = `Hide ${hiderButtonsKeys[i]}`;
            } else {
                for (var j = 0; j < hiderEntries[i].length; j++) {
                    hiderEntries[i][j].classList.add("hidden");
                }
                for (var j = 0; j < hiderCollapsibles[i].length; j++) {
                    hiderCollapsibles[i][j].classList.add("hidden");
                    hiderCollapsibles[i][j].nextElementSibling.classList.add("hidden");
                    hiderCollapsibles[i][j].classList.remove("active");
                }
                hiderButtons[i].classList.add("off");
                hiderButtons[i].innerHTML = `Show ${hiderButtonsKeys[i]}`;
            }
            // reopen collapsibles to make space for the new entries
            for (var j = 0; j < scenarioOutlines.length; j++) {
                scenarioOutlines[j].click();
                scenarioOutlines[j].click();
            }
        }
    }
    // toggleSkippedButton.click();


    // load hash
    var hash = window.location.hash.substr(1);
    for (var j = 0; j < testContents.length; j++) {
        //testContents[j].classList.add("hidden");
        if (testContents[j].id.replace("scenario-", "") == hash) {
            testContents[j].classList.remove("hidden");
            document.getElementById("single-test-placeholder").classList.add("hidden");
            break;
        }
    }

}, false);


function set_hash(value) {
    window.location.hash = `#${value}`
}