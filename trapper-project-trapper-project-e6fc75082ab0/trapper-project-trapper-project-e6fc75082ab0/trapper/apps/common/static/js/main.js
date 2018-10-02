'use strict';

(function(global, namespace) {

var alert = global[namespace].Alert || {};

var module = {
	run: function() {
		alert.init();

		this.initActiveApp();

		// this.uploaderForms();
	},

	initActiveApp: function() {
		var appInfo = global.document.body.dataset.app;
		if(!appInfo) { return; }

		appInfo = appInfo.split('::');
		var appName = appInfo[0][0].toUpperCase() + appInfo[0].slice(1);

		var activeApp = global[namespace][appName];
		if(activeApp.hasOwnProperty(appInfo[1])) {
			activeApp[appInfo[1]].call(activeApp);
		} else {
			activeApp.init();
		}
	},

	// uploaderForms: function() {
	// 	var uploaders = [];

	// 	function Uploader(form, url) {
	// 		var _this = this;

	// 		this.form = form;
	// 		this.fileInputs = this.form.querySelectorAll('input[type=file]');
	// 		this.progressBar = this.form.querySelector('.progress-bar');
	// 		this.url = url;
	// 		this.uploading = false;

	// 		this.preventClosing(true);

	// 		this.form.addEventListener('submit', function(e) {
	// 			e.preventDefault();

	// 			_this.submitForm();
	// 		});
	// 	}

	// 	Uploader.prototype.preventClosing = function() {
	// 		var _this = this;

	// 		function prevent(event) {
	// 			if(!_this.uploading) { return null; }

	// 			var message = 'If you reload your uploading process the archive collection will be lost.';

	// 			if (typeof event === undefined) {
	// 				event = window.event;
	// 			}
	// 			if (event ) {
	// 				event.returnValue = message;
	// 			}

	// 			return message;
	// 		}

	// 		window.addEventListener('beforeunload', prevent, false);
	// 	};

	// 	Uploader.prototype.setProgress = function(value) {
	// 		this.progressBar.style.width = value + '%';
	// 	};

	// 	Uploader.prototype.setFormData = function(formData) {
	// 		var fields = this.form.querySelectorAll('input:not([type="file"]), textarea, select');

	// 		[].forEach.call(fields, function(field) {
	// 			if(!field.name) { return; }
				
	// 			formData.append(field.name, field.value);
	// 		});

	// 		console.log(fields, formData);
	// 	};

	// 	Uploader.prototype.submitForm = function() {
	// 		if(this.uploading) { return; }

	// 		this.uploading = true;

	// 		var req = this.createRequest('POST', this.url);

	// 		var formData = new FormData();
	// 		[].forEach.call(this.fileInputs, function(fileInput) {
	// 			for(var i = 0; i < fileInput.files.length; i++) {
	// 				formData.append(fileInput.name, fileInput.files[i]);
	// 			}
	// 		});

	// 		this.setFormData(formData);			

	// 		this.setProgress(0);

	// 		req.send(formData);
	// 	};

	// 	Uploader.prototype.createRequest = function(type, url) {
	// 		var req = new XMLHttpRequest();

	// 		req.upload.addEventListener('progress', this.progress.bind(this), false);
	// 		req.addEventListener('load', this.success.bind(this), false);
	// 		req.addEventListener('error', this.error.bind(this), false);
	// 		req.addEventListener('abort', this.abort.bind(this), false);

	// 		req.open(type, url, true);

	// 		return req;
	// 	};

	// 	Uploader.prototype.success = function(event) {
	// 		console.log('success: ', event);
	// 		alert.success('File uploaded succesfully.');

	// 		this.uploading = false;
	// 		this.setProgress(100);
	// 		this.progressBar.classList.add('progress-bar-success');
	// 	};

	// 	Uploader.prototype.error = function(event) {
	// 		console.log('error: ', event);
	// 		alert.error(event.data.msg);

	// 		this.uploading = false;
	// 		this.progressBar.classList.add('progress-bar-danger');
	// 	};

	// 	Uploader.prototype.progress = function(event) {
	// 		console.log('progress: ', event);

	// 		if(this.uploadingId) { return; }

	// 		this.setProgress((event.loaded / event.total) * 100);
	// 	};

	// 	Uploader.prototype.abort = function(event) {
	// 		console.log('abort: ', event);

	// 		this.uploading = false;
	// 		this.progressBar.classList.add('progress-bar-warning');
	// 	};

	// 	var forms = document.querySelectorAll('.form-uploader');

	// 	if(!forms.length) { return; }

	// 	[].forEach.call(forms, function(form) {
	// 		uploaders.push(new Uploader(form, form.action));
	// 	});
	// }
};

// safe way to handle DOM ready event
function DOMready() {
	window.document.removeEventListener('DOMContentLoaded', DOMready);
	module.run();
}
if(document.readyState === 'complete') {
	module.run();
} else {
	window.document.addEventListener('DOMContentLoaded', DOMready);
}

}(window, 'TrapperApp'));
