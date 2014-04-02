#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""Statistics collection classes."""



import bisect
import functools
import threading
import time


from grr.lib import registry
from grr.lib import utils


# Stats decorators
class Timed(object):
  """A decorator to automatically export timing info for function calls."""

  def __init__(self, varname, fields=None):
    self.varname = varname
    self.fields = fields or []

  def __call__(self, func):

    @functools.wraps(func)
    def Decorated(*args, **kwargs):
      start_time = time.time()
      res = None
      try:
        res = func(*args, **kwargs)
      finally:
        total_time = time.time() - start_time
        STATS.RecordEvent(self.varname, total_time, fields=self.fields)

      return res

    return Decorated


class Counted(object):
  """A decorator to automatically count function calls."""

  def __init__(self, varname, fields=None):
    self.varname = varname
    self.fields = fields or []

  def __call__(self, func):

    @functools.wraps(func)
    def Decorated(*args, **kwargs):
      try:
        res = func(*args, **kwargs)
      finally:
        STATS.IncrementCounter(self.varname, fields=self.fields)
      return res

    return Decorated


class CountingExceptionMixin(object):
  """Each time this exception is raised we increment the counter."""
  # Override with the name of the counter
  counter = None
  # Override with fields set for this counter
  fields = []

  def __init__(self, *args, **kwargs):
    if self.counter:
      STATS.IncrementCounter(self.counter, fields=self.fields)
    super(CountingExceptionMixin, self).__init__(*args, **kwargs)


class _Metric(object):
  """Base class for all the metrics."""

  def __init__(self, fields_defs, docstring, units):
    self.fields_defs = fields_defs
    self.docstring = docstring
    self.units = units
    self._values = {}

  def _FieldsToKey(self, fields):
    if not fields:
      return ("__default__",)
    else:
      return tuple(fields)

  def _DefaultValue(self):
    return ""

  def Get(self, fields=None):
    """Gets this metric's value corresponding to the given fields values."""
    if self.fields_defs is None and fields is not None:
      raise ValueError("Metric was registered without fields, "
                       "but following fields were provided: %s." % fields)

    if self.fields_defs is not None and fields is None:
      raise ValueError("Metric was registered with fields (%s), "
                       "but no fields were provided." % self.fields_defs)

    if (self.fields_defs is not None and fields is not None and
        len(self.fields_defs) != len(fields)):
      raise ValueError("Metric was registered with %d fields (%s), but "
                       "%d fields were provided (%s)." % (len(self.fields_defs),
                                                          self.fields_defs,
                                                          len(fields),
                                                          fields))

    try:
      return self._values[self._FieldsToKey(fields)]
    except KeyError:
      return self._DefaultValue()

  def ListFieldsValues(self):
    """Lists all fields values that were used with this metric."""
    if self.fields_defs:
      return self._values.iterkeys()
    else:
      return []


class _CounterMetric(_Metric):
  """Simple counter metric."""

  def _DefaultValue(self):
    return 0

  def Increment(self, delta, fields=None):
    """Increments counter value by a given delta."""
    if delta < 0:
      raise ValueError("Delta should be > 0 (not %d)" % delta)

    key = self._FieldsToKey(fields)
    if key in self._values:
      self._values[key] += delta
    else:
      self._values[key] = delta


class Distribution(object):
  """Statistics for a particular type of event."""

  def __init__(self, bins):
    self.sum = 0
    self.count = 0
    self.bins_heights = {}
    self.bins = [-float("inf")] + bins
    for b in self.bins:
      self.bins_heights[b] = 0

  def Record(self, value):
    """Records given value."""
    self.sum += value
    self.count += 1

    pos = bisect.bisect(self.bins, value) - 1
    if pos < 0:
      pos = 0
    elif pos == len(self.bins):
      pos = len(self.bins)

    b = self.bins[pos]
    self.bins_heights[b] += 1


class _EventMetric(_Metric):
  """EventMetric provides detailed stats, like averages, distribution, etc."""

  def _DefaultValue(self):
    return Distribution(self._bins)

  def __init__(self, bins, fields, docstring, units):
    self._bins = bins or [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1,
                          1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9, 10,
                          15, 20, 50, 100]
    super(_EventMetric, self).__init__(fields, docstring, units)

  def Record(self, value, fields=None):
    """Records given value."""
    key = self._FieldsToKey(fields)

    try:
      entry = self._values[key]
    except KeyError:
      entry = Distribution(self._bins)
      self._values[key] = entry

    entry.Record(value)


class _GaugeMetric(_Metric):
  """Gague metric is a simple variable-like metric."""

  def _DefaultValue(self):
    return self.value_type()

  def __init__(self, value_type, fields, docstring, units):
    self.value_type = value_type
    super(_GaugeMetric, self).__init__(fields, docstring, units)

  def Set(self, value, fields=None):
    """Sets metric's current value to a given value."""
    key = self._FieldsToKey(fields)
    self._values[key] = self.value_type(value)

  def SetCallback(self, callback, fields=None):
    """Attaches callback to the metric."""
    key = self._FieldsToKey(fields)
    self._values[key] = callback

  def Get(self, fields=None):
    """Returns current metric's value (executing callback if needed)."""
    result = super(_GaugeMetric, self).Get(fields=fields)
    if hasattr(result, "__call__"):
      return result()
    else:
      return result


class MetricType(object):
  """Available metrics types. Used when inspecting metrics metadata."""
  COUNTER = "counter"
  GAUGE = "gauge"
  EVENT = "event"


class MetricUnits(object):
  """Available metrics units. Used when registering metrics."""
  SECONDS = "seconds"
  MILLISECONDS = "milliseconds"
  MICROSECONDS = "microseconds"
  NANOSECONDS = "nanoseconds"

  BITS = "bits"
  BYTES = "bytes"
  KILOBYTES = "kilobytes"
  MEGABYTES = "megabytes"
  GIGABYTES = "gigabytes"


class MetricMetadata(object):
  """Metrics metadata."""

  def __init__(self, varname=None, metric_type=None, value_type=None,
               fields_defs=None, docstring=None, units=None):
    self.varname = varname
    self.metric_type = metric_type
    self.value_type = value_type
    self.fields_defs = fields_defs
    self.docstring = docstring
    self.units = units


class StatsCollector(object):
  """This class keeps tabs on stats."""

  def __init__(self):
    self._metrics = {}
    self.lock = threading.Lock()
    self._metrics_metadata = {}

  def RegisterCounterMetric(self, varname, fields=None, docstring=None,
                            units=None):
    """Registers a counter metric (integer value that never decreases).

    Args:
      varname: Metric name.
      fields: Metric dimensions. For example, "renderer_latency" metric may
              have "renderer_name" dimension. Fields are provided as list of
              tuples, like: [("renderer_name", string)].
      docstring: Metric description.
      units: Metric units (see stats.MetricUnits for details).

    If metric with the same name was registered before, it will be overwritten.
    """
    self._metrics[varname] = _CounterMetric(fields, docstring, units)
    self._metrics_metadata[varname] = MetricMetadata(
        varname=varname, metric_type=MetricType.COUNTER, value_type=int,
        fields_defs=fields, docstring=docstring, units=units)

  @utils.Synchronized
  def IncrementCounter(self, varname, delta=1, fields=None):
    """Increments a counter metric by a given delta.

    Args:
      varname: Metric name.
      delta: Delta by which the metric should be incremented.
      fields: Values for this metric's fields. For example, if metric
              was registered with fields like
              [("flow_type", int), ("user_type", int)], then for that metric
              fields argument may look like: fields=[10, 12]. Should be None
              if the metric was registered without any fields.

    Raises:
      ValueError: If delta < 0.
    """
    self._metrics[varname].Increment(delta, fields)

  def RegisterEventMetric(self, varname, bins=None, fields=None,
                          docstring=None, units=None):
    """Registers metric that records distribution of values.

    Args:
      varname: Metric name.
      bins: Bins used to store distribution information. For example,
            [0, 0.1, 0.2] will create 4 bins: -Infinity..0, 0..0.1, 0.1..0.2,
            0.2..+Infinity.
      fields: Metric dimensions. For example, "renderer_latency" metric may
              have "renderer_name" dimension. Fields are provided as list of
              tuples, like: [("renderer_name", string)].
      docstring: Metric description.
      units: Metric units (see stats.MetricUnits for details).

    If metric with the same name was registered before, it will be overwritten.
    """
    self._metrics[varname] = _EventMetric(bins, fields, docstring, units)
    self._metrics_metadata[varname] = MetricMetadata(
        varname=varname, metric_type=MetricType.EVENT, fields_defs=fields,
        docstring=docstring, units=units)

  @utils.Synchronized
  def RecordEvent(self, varname, value, fields=None):
    """Records value corresponding to the given event metric.

    Args:
      varname: Metric name.
      value: Value to be recorded.
      fields: Values for this metric's fields. For example, if metric
              was registered with fields like
              [("flow_type", int), ("user_type", int)], then for that metric
              fields argument may look like: fields=[10, 12]. Should be None
              if the metric was registered without any fields.
    """
    self._metrics[varname].Record(value, fields)

  def RegisterGaugeMetric(self, varname, value_type, fields=None,
                          docstring=None, units=None):
    """Registers metric that may change arbitrarily.

    Args:
      varname: Metric name.
      value_type: Can be: int, long, float, str, bool.
      fields: Metric dimensions. For example, "renderer_latency" metric may
              have "renderer_name" dimension. Fields are provided as list of
              tuples, like: [("renderer_name", string)].
      docstring: Metric description.
      units: Metric units (see stats.MetricUnits for details).

    If metric with the same name was registered before, it will be overwritten.
    """
    self._metrics[varname] = _GaugeMetric(value_type, fields, docstring, units)
    self._metrics_metadata[varname] = MetricMetadata(
        varname=varname, metric_type=MetricType.GAUGE, value_type=value_type,
        fields_defs=fields, docstring=docstring, units=units)

  @utils.Synchronized
  def SetGaugeValue(self, varname, value, fields=None):
    """Sets value of a given gauge metric.

    Args:
      varname: Metric name.
      value: New metric value.
      fields: Values for this metric's fields. For example, if metric
              was registered with fields like
              [("flow_type", int), ("user_type", int)], then for that metric
              fields argument may look like: fields=[10, 12]. Should be None
              if the metric was registered without any fields.
    """
    self._metrics[varname].Set(value, fields)

  @utils.Synchronized
  def SetGaugeCallback(self, varname, callback, fields=None):
    """Attached callback to the gauge metric.

    Args:
      varname: Metric name.
      callback: Callback function. This function is called everytime
                this metric's value (with corresponding fields values) is
                queried. Called without any arguments.
      fields: Values for this metric's fields. For example, if metric
              was registered with fields like
              [("flow_type", int), ("user_type", int)], then for that metric
              fields argument may look like: fields=[10, 12]. Should be None
              if the metric was registered without any fields. If not None,
              callback will only be called when caller provides same fields
              values.
    """
    self._metrics[varname].SetCallback(callback, fields)

  def GetMetricMetadata(self, varname):
    """Returns stats.MetricMetadata for a metric with a given name.

    Args:
      varname: Metric name.

    Returns:
      stats.MetricMetadata object describing the metric.

    Raises:
      KeyError: if metric is not found.
    """
    return self._metrics_metadata[varname]

  def GetAllMetricsMetadata(self):
    """Returns dictionary with metadata for all the registered metrics.

    Note, that the dictionary may get mutated after it's returned to a caller.
    Mutations are unlikely, though, as most metrics are registered early
    in the application's lifetime.

    Returns:
      Dictionary of (metric name, stats.MetricMetadata).
    """
    return self._metrics_metadata

  def GetMetricFields(self, varname):
    """Returns all fields values for a metric with a given name.

    Args:
      varname: Metric name.

    Returns:
      List of all fields values that were used for the specified metric. For
      example, if there's a counter metric registered with fields
      ("renderer_type", int) and there were 2 calls to Increment:
      Increment("renderer_type", fields=[1]),
      Increment("renderer_type", fields=[2]), then
      GetMetricFields("renderer_type") will return [(1,), (2,)].
    """
    return self._metrics[varname].ListFieldsValues()

  def GetMetricValue(self, varname, fields=None):
    """Returns metric value of a given metric for given fields values.

    Args:
      varname: Metric name:
      fields: Values for this metric's fields. For example, if metric
              was registered with fields like
              [("flow_type", int), ("user_type", int)], then for that metric
              fields argument may look like: fields=[10, 12]. Should be None
              if the metric was registered without any fields.

    Returns:
      int for a counter metric.
      int, long, float, str or bool (depending on the type used to register
        the metric) for a gauge metric.
      Distribtion-compatible object for event metric. Distribution-compatible
      means "with an API matching the API of the Distribution object".
    """
    return self._metrics[varname].Get(fields)


# A global store of statistics.
STATS = None


class StatsInit(registry.InitHook):
  """Initialize stats collector."""
  pass

