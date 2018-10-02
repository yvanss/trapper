L.Storage.Map.prototype.enableEdit = function (e) {
    L.DomUtil.addClass(document.body, "storage-edit-enabled");
    this.editEnabled = true;
    L.Storage.fire('ui:startedit', {
        data: this
    });
};

L.Storage.Map.prototype.disableEdit = function (e) {
    L.DomUtil.removeClass(document.body, "storage-edit-enabled");
    this.editEnabled = false;
    L.Storage.fire('ui:endedit', {
        data: this
    });
};

// Fixing _pointToLayer error
L.Storage.DataLayer.prototype._pointToLayer = function (geojson, latlng) {
    if (this.options.pointToLayer) {
       return this.options.pointToLayer(geojson, latlng);
    }
    return new L.Storage.Marker(
        this.map,
        latlng, {
            "geojson": geojson,
            "datalayer": this
        }
    );
};

var _isReadOnly = L.Storage.Marker.prototype.isReadOnly;
L.Storage.Marker.prototype.isReadOnly = function () {
    if (this.datalayer && this.datalayer.options.trapperLayer) {
        return false;
    }
    return this.datalayer && this.datalayer.isRemoteLayer();
};

L.Storage.Icon.prototype._getColor = function () {
    var color;
    if (this.feature && this.feature.color) {
        color = this.feature.color;
    } else if (this.options.color) {
        color = this.options.color;
    } else if (this.feature) {
        color = this.feature.getOption("color");
    } else {
        color = this.map.getDefaultOption('color');
    }
    return color;
};

L.Storage.Icon.prototype._getIconUrl = function (name) {
    var url;
    if (this.feature && this.feature._selected) {
        url = '/static/geomap/img/dot.png';
    } else if (this.feature && this.feature._getIconUrl(name)) {
        url = this.feature._getIconUrl(name);
    } else {
        url = this.options[name + 'Url'];
    }
    return this.formatUrl(url, this.feature);
};

/*
  the current version of leaflet.Storage does not support
  Rectangles and Circles
*/

L.Storage.Rectangle = L.Rectangle.extend({
    parentClass: L.Rectangle,
    includes: [L.Storage.FeatureMixin, L.Storage.PathMixin, L.Mixin.Events],

    isSameClass: function (other) {
        return other instanceof L.S.Rectangle;
    },
    getClassName: function () {
        return 'rectangle';
    },
});
L.Storage.Editable.prototype.createRectangle = function (latlngs) {
    var rectangle = new L.Storage.Rectangle(this.map, latlngs);
    return rectangle;
};

L.Storage.Circle = L.Circle.extend({
    parentClass: L.Circle,
    includes: [L.Storage.FeatureMixin, L.Storage.PathMixin, L.Mixin.Events],

    isSameClass: function (other) {
        return other instanceof L.S.Circle;
    },
    getClassName: function () {
        return 'circle';
    },
});
L.Storage.Editable.prototype.createCircle = function (latlng) {
    var circle = new L.Storage.Circle(this.map, latlng);
    return circle;
};
