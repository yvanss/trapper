'use strict';

(function (global, namespace, moduleName) {

    var module = {};

    var plugins = global[namespace].Plugins;
    var alert = global[namespace].Alert;
    var modal = global[namespace].Modal;
    var uploader = global[namespace].Uploader;

    var doc = global.document;

    var comments = function () {
        var replyBtns = doc.querySelectorAll('.btn-reply');
        var parentId = doc.querySelector('#id_parent');
        var message = doc.querySelector('#id_comment');
        var commentTab = doc.querySelector('#tab-comment-form');

        function reply(event) {
            parentId.value = event.target.parentNode.parentNode.parentNode.dataset.pk;
            commentTab.click();
            message.focus();
        }

        [].forEach.call(replyBtns, function (btn) {
            btn.addEventListener('click', reply);
        });
    };

    var classifications = function () {
        function getInfo(btn) {
            var td = btn.parentNode.parentNode.querySelectorAll('td');

            return 'Creator: ' + td[0].innerHTML + ', Date: ' + td[1].innerHTML;
        }

        var deleteBtns = doc.querySelectorAll('.btn-delete'),
            approveBtns = doc.querySelectorAll('.btn-approve');

        [].forEach.call(deleteBtns, function (btn) {
            btn.addEventListener('click', function (event) {
                event.preventDefault();

                var target = event.target;

                if (target.tagName.toLowerCase() === 'span') {
                    target = target.parentNode;
                }

                modal.confirm({
                    title: 'Do you want to delete the classification?',
                    content: getInfo(btn),
                    buttons: [{
                        type: 'danger',
                        label: 'Yes',
                        onClick: function () {
                            global.location = target.href;
                        }
                    }, {
                        type: 'default',
                        label: 'Cancel'
                    }]
                });
            });
        });

        [].forEach.call(approveBtns, function (btn) {
            btn.addEventListener('click', function (event) {
                event.preventDefault();

                var target = event.target;

                if (target.tagName.toLowerCase() === 'span') {
                    target = target.parentNode;
                }

                modal.confirm({
                    title: 'Do you want to approve the classification?',
                    content: getInfo(btn),
                    buttons: [{
                        type: 'success',
                        label: 'Yes',
                        onClick: function () {
                            send(target.href);
                        }
                    }, {
                        type: 'default',
                        label: 'Cancel'
                    }]
                });
            });
        });

        function c(k) {
            return (doc.cookie.match('(^|; )' + k + '=([^;]*)') || 0)[2];
        }

        function send(url) {
            var sender = doc.createElement('form'),
                csrf = doc.createElement('input');

            sender.method = 'POST';
            sender.action = url;

            csrf.type = 'hidden';
            csrf.name = 'csrfmiddlewaretoken';
            csrf.value = c('csrftoken');

            sender.appendChild(csrf);

            doc.body.appendChild(sender);

            sender.submit();
        }
    };

    var videoPlayer;
    var player = function (id) {
        var video = doc.getElementById(id);

        if (!video) {
            return;
        }

        videoPlayer = global.videojs(video, {}, function () {
            // Player (this) is initialized and ready.
        });

        videoPlayer.rangeslider({});
        videoPlayer.showSlider();
        videoPlayer.hideSliderPanel();
    };

    function leftPad(number, targetLength) {
        var output = number + '';
        while (output.length < targetLength) {
            output = '0' + output;
        }
        return output;
    }

    function secondsToTime(secs) {
        secs = Math.round(secs);
        var hours = Math.floor(secs / (60 * 60));
        var divisor_for_minutes = secs % (60 * 60);
        var minutes = Math.floor(divisor_for_minutes / 60);
        var divisor_for_seconds = divisor_for_minutes % 60;
        var seconds = Math.ceil(divisor_for_seconds);
        return leftPad(hours, 2) + ':' + leftPad(minutes, 2) + ':' + leftPad(seconds, 2);
    }

    function timeToSeconds(time) {
        var timeS = time.split(':')
        return parseInt(timeS[0], 10) * 3600 + parseInt(timeS[1], 10) * 60 + parseInt(timeS[2], 10);
    }

    var annotations = function (box) {
        var inputFrom, inputTo;
        var btnSet, btnGet, btnPlay;

        var inputs = box.querySelectorAll('input');

        inputFrom = inputs[0];
        inputTo = inputs[1];

        btnSet = box.querySelector('.btn-set');
        btnGet = box.querySelector('.btn-get');
        btnPlay = box.querySelector('.btn-play');

        if (btnGet) {
            btnGet.addEventListener('click', function (e) {
                e.preventDefault();

                var time = videoPlayer.getValueSlider();

                inputFrom.value = secondsToTime(time.start);
                inputTo.value = secondsToTime(time.end);
            });
        }

        if (btnSet) {
            btnSet.addEventListener('click', function (e) {
                e.preventDefault();

                var start = timeToSeconds(inputFrom.value);
                var end = timeToSeconds(inputTo.value);

                videoPlayer.setValueSlider(start, end);
            });
        }

        if (btnPlay) {
            btnPlay.addEventListener('click', function (e) {
                e.preventDefault();

                videoPlayer.play();

                setTimeout(function () {
                    var start = timeToSeconds(inputFrom.value);
                    var end = timeToSeconds(inputTo.value);

                    videoPlayer.loopBetween(start, end);
                });
            });
        }
    };

    var repeatbleTable = function (table, cb) {
        var namePrefix = table.dataset.name;
        var tbody = table.querySelector('tbody');
        //var template = tbody.querySelector('tr:last-child').innerHTML;
        var template = doc.querySelector('#dynamic-form-row-template').innerHTML;

        var reg = new RegExp('(' + namePrefix + '-)(__prefix__)', 'g');

        var totalInput = doc.querySelector('input[name=' + namePrefix + '-TOTAL_FORMS]'),
            filledInput = doc.querySelector('input[name=' + namePrefix + '-INITIAL_FORMS]'),
            maxInput = doc.querySelector('input[name=' + namePrefix + '-MAX_NUM_FORMS]');

        var filled = parseInt(filledInput.value, 10),
            max = parseInt(maxInput.value, 10),
            total = parseInt(totalInput.value, 10);

        var index = total;
        table.addEventListener('click', function (event) {
            var target = event.target;

            if (target.tagName.toLowerCase() === 'span') {
                target = target.parentNode;
            }

            if (target.tagName.toLowerCase() === 'button' && target) {
                if (target.classList.contains('btn-add-row')) {
                    addRow(target);
                } else if (target.classList.contains('btn-remove-row')) {
                    removeRow(target);
                }
            }
        });

        function createRow() {
            var row = doc.createElement('tr');
            row.innerHTML = template.replace(reg, '$1' + index);
            return row;
        }

        function updateInputs() {
            totalInput.value = total;
        }

        function addRow(target) {
            if (filled >= max) {
                return;
            }

            var row = createRow();
            tbody.appendChild(row);
            plugins.select2();
            var ann = row.querySelector('.form-annotation');
            if (ann) {
                annotations(ann);
            }

            index++;
            total++;
            updateInputs();
        }

        function removeRow(target) {
            var row = target.parentNode.parentNode;
            var checkbox = row.querySelector('td:last-child input[type=checkbox]');

            if (checkbox) {
                checkbox.checked = true;
                row.style.display = 'none';
            } else {
                row.remove();
                total--;
                updateInputs();
            }
        }
    };


    var repeatableTabs = function (tabs) {
        var namePrefix = tabs.dataset.name;

        var createBtn = tabs.querySelector('.tab-create');
        var tabsNav = tabs.querySelector('.nav-tabs');
        var tabsContainer = tabs.querySelector('.tab-content');
        var dynamicTabs = tabs.querySelectorAll('div[id^="tab-dynamic"]');

        if (!dynamicTabs) {
            return;
        }

        var template = doc.querySelector('#tab-dynamic-template').innerHTML;
        //var template = dynamicTabs[dynamicTabs.length - 1].innerHTML;

        var reg = new RegExp('(' + namePrefix + '-)(__prefix__)', 'g');

        var totalInput = doc.querySelector('input[name=' + namePrefix + '-TOTAL_FORMS]'),
            filledInput = doc.querySelector('input[name=' + namePrefix + '-INITIAL_FORMS]'),
            maxInput = doc.querySelector('input[name=' + namePrefix + '-MAX_NUM_FORMS]');

        var filled = parseInt(filledInput.value, 10),
            max = parseInt(maxInput.value, 10),
            total = parseInt(totalInput.value, 10);

        var index = total;

        createBtn.addEventListener('click', function (e) {
            e.preventDefault();

            addTab();
        });

        tabsNav.addEventListener('click', function (event) {
            var target = event.target;

            if (target.tagName.toLowerCase() === 'span') {
                target = target.parentNode;
            }

            if (target.tagName.toLowerCase() === 'button' && !target.classList.contains('btn-success')) {
                removeTab(target);
            }
        });

        function updateInputs() {
            totalInput.value = total;
        }

        function addTab() {
            if (filled >= max) {
                return;
            }

            index++;
            total++;
            updateInputs();

            var tab = doc.createElement('li');
            tab.innerHTML = '<a href="#tab-dynamic-' + index + '" data-toggle="tab"><strong>#' + index + ' Dynamic</strong> <button class="btn btn-danger btn-xs"><span class="fa fa-remove"></span></button></a>';

            var tabContent = doc.createElement('div');
            tabContent.className = 'tab-pane';
            tabContent.id = 'tab-dynamic-' + index;
            tabContent.innerHTML = template.replace(reg, '$1' + (index - 1));

            tabsNav.insertBefore(tab, createBtn);
            tabsContainer.appendChild(tabContent);
            plugins.select2();

            var ann = tabContent.querySelector('.form-annotation');
            if (ann) {
                annotations(ann);
            }

            tab.querySelector('a').click();
        }

        function removeTab(btn) {
            var tab = btn.parentNode.parentNode;
            var pane = doc.querySelector(btn.parentNode.hash);

            var checkbox = pane.querySelector('input[type=checkbox][hidden]');

            var prevTab = tab.previousSibling;
            while (prevTab.nodeType !== 1) {
                prevTab = prevTab.previousSibling;
            }

            if (checkbox) {
                checkbox.checked = true;
                tab.remove();
                pane.style.display = 'none';
            } else {
                tab.remove();
                pane.remove();
                total--;
                updateInputs();
            }

            prevTab.querySelector('a').click();
        }
    };

    var sliderNav = function () {
        var slider = doc.querySelector('.panel-scroll');
        var btnFirst = doc.querySelector('.btn-first');
        var btnLast = doc.querySelector('.btn-last');
        var btnCurrent = doc.querySelector('.btn-current');

        btnFirst.addEventListener('click', function (e) {
            e.preventDefault();

            slider.scrollLeft = 0;
        });

        btnLast.addEventListener('click', function (e) {
            e.preventDefault();

            slider.scrollLeft = slider.scrollWidth;
        });

        btnCurrent.addEventListener('click', function (e) {
            e.preventDefault();

            slider.scrollLeft = slider.querySelector('.current').offsetLeft - 360;
        });
    };

    var media = function () {
        var medias = doc.querySelectorAll('[data-media]');

        if (!medias.length) {
            return;
        }

        [].forEach.call(medias, function (media) {
            media.addEventListener('click', function (event) {
                event.preventDefault();

                modal[media.dataset.media](media.href);
            });
        });
    };

    module.init = function () {
        console.log(moduleName + ' initialize');
        plugins.collapsable();
    };

    module.upload = function () {
        plugins.fileInputs();
        plugins.select2();
    };

    module.update = module.create = function () {
        [].forEach.call(doc.querySelectorAll('.table-repeatable'), function (table) {
            plugins.repeatbleTable(table);
        });
        plugins.select2();
    };

    module.preview = function () {
        media();

        sliderNav();

        comments();

        classifications();

        player('trapper-video-player');

        plugins.select2();

    };

    module.classify = function () {
        media();

        sliderNav();

        comments();

        classifications();

        player('trapper-video-player');

        [].forEach.call(doc.querySelectorAll('.tabs-repeatable'), repeatableTabs);

        [].forEach.call(doc.querySelectorAll('.table-repeatable'), repeatbleTable);

        [].forEach.call(doc.querySelectorAll('.form-annotation'), annotations);

        plugins.select2();
    };

// if passed namespace does not exist, create one
    global[namespace] = global[namespace] || {};

// append module to given namespace
    global[namespace][moduleName] = module;

}(window, 'TrapperApp', 'Classification'));
